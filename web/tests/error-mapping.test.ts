/**
 * How API errors reach the person looking at the screen (M6).
 *
 * The server actions are exercised directly with the API client mocked out, so these
 * stay pure: no network, no browser, no database. What is pinned here is the mapping
 * from `{status, code}` to a field message, a calm notice or a generic fallback.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/cache", () => ({ revalidatePath: vi.fn() }));
vi.mock("next/navigation", () => ({
  redirect: vi.fn((url: string) => {
    // The real redirect() signals by throwing; mimic that so callers behave the same.
    throw new Error(`NEXT_REDIRECT:${url}`);
  }),
}));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    createLead: vi.fn(),
    updateLeadState: vi.fn(),
    assignLead: vi.fn(),
    trackLead: vi.fn(),
  };
});
vi.mock("@/lib/auth", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/auth")>();
  return { ...actual, getToken: vi.fn(async () => null as string | null) };
});

import { submitApplication, type ApplyState } from "@/app/(public)/apply/actions";
import { changeLeadState, assignToMe } from "@/app/(internal)/leads/actions";
import { lookupStatus } from "@/app/(public)/status/actions";
import { ApiError, assignLead, createLead, trackLead, updateLeadState } from "@/lib/api";
import { getToken } from "@/lib/auth";

const LEAD_ID = "11111111-1111-4111-8111-111111111111";
/** A token whose payload decodes to the signed-in attorney. Display use only. */
const TOKEN = `header.${Buffer.from('{"sub":"attorney@example.com","name":"Alex Chen"}').toString(
  "base64url",
)}.signature`;

/** A form the client-side schema is happy with, so only the API's answer is on trial. */
function validForm(): FormData {
  const form = new FormData();
  form.set("first_name", "Ada");
  form.set("last_name", "Lovelace");
  form.set("email", "ada@example.com");
  form.set("website", "");
  form.set("resume", new File([new Uint8Array(64)], "cv.pdf", { type: "application/pdf" }));
  return form;
}

function apply(error?: ApiError): Promise<ApplyState> {
  if (error) vi.mocked(createLead).mockRejectedValueOnce(error);
  return submitApplication({}, validForm());
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(getToken).mockResolvedValue(TOKEN);
});

describe("apply form — API errors land on the field the applicant can fix", () => {
  it("413 resume_too_large → a message on the résumé field", async () => {
    const state = await apply(new ApiError(413, "Resume exceeds 5 MB", "resume_too_large"));
    expect(state).toEqual({ fieldErrors: { resume: "Your file must be 5 MB or smaller." } });
  });

  it("415 unsupported_media_type → the API's message on the résumé field", async () => {
    const state = await apply(
      new ApiError(415, "Only PDF and DOCX files are accepted", "unsupported_media_type"),
    );
    expect(state.fieldErrors?.resume).toBe("Only PDF and DOCX files are accepted");
    expect(state.formError).toBeUndefined();
  });

  it("422 validation_error → the prefixed field gets the message", async () => {
    const state = await apply(
      new ApiError(422, "email: value is not a valid email address", "validation_error"),
    );
    expect(state).toEqual({ fieldErrors: { email: "value is not a valid email address" } });
  });

  it("422 validation_error with an unknown prefix → a form-level message", async () => {
    const state = await apply(new ApiError(422, "body: malformed multipart", "validation_error"));
    expect(state.formError).toBe("body: malformed multipart");
    expect(state.fieldErrors).toBeUndefined();
  });

  it("503 storage_unavailable → a form-level message that says nothing was saved", async () => {
    const state = await apply(new ApiError(503, "storage down", "storage_unavailable"));
    expect(state.formError).toMatch(/nothing was saved/i);
  });

  it("an unknown error → a generic form-level message, never the raw detail", async () => {
    const state = await apply(new ApiError(500, "Traceback (most recent call last)", "boom"));
    expect(state.formError).toBe(
      "Something went wrong submitting your application. Please try again.",
    );
    expect(JSON.stringify(state)).not.toContain("Traceback");
  });

  it("a locally invalid form never reaches the API", async () => {
    const form = validForm();
    form.set("email", "not-an-email");
    const state = await submitApplication({}, form);
    expect(state.fieldErrors?.email).toBe("Enter a valid email address");
    expect(createLead).not.toHaveBeenCalled();
  });

  it("forwards the honeypot untouched so the API decides (SEC4)", async () => {
    const form = validForm();
    // contact_ref_2, not "website": Chrome autofill filled the old name for real
      // applicants and got them silently dropped (NOTES.md #17).
      form.set("contact_ref_2", "http://spam.example");
    vi.mocked(createLead).mockResolvedValueOnce({} as never);
    await expect(submitApplication({}, form)).rejects.toThrow("NEXT_REDIRECT:/thank-you");
    const sent = vi.mocked(createLead).mock.calls[0][0];
    expect(sent.get("contact_ref_2")).toBe("http://spam.example");
  });
});

describe("changeLeadState — the 409 vocabulary (FR8)", () => {
  it("409 already_in_state → a calm notice, not an error", async () => {
    vi.mocked(updateLeadState).mockRejectedValueOnce(
      new ApiError(409, "Lead is already REACHED_OUT", "already_in_state"),
    );
    const result = await changeLeadState(LEAD_ID, "REACHED_OUT");
    expect(result.status).toBe("already");
    expect(result.message).toBe("Already in that state — list refreshed.");
  });

  it("409 invalid_transition → an error carrying the API's explanation", async () => {
    vi.mocked(updateLeadState).mockRejectedValueOnce(
      new ApiError(409, "Cannot move QUALIFIED to PENDING", "invalid_transition"),
    );
    const result = await changeLeadState(LEAD_ID, "PENDING");
    expect(result).toEqual({ status: "error", message: "Cannot move QUALIFIED to PENDING" });
  });

  it("401 → asks the attorney to sign in again", async () => {
    vi.mocked(updateLeadState).mockRejectedValueOnce(
      new ApiError(401, "Not authenticated", "unauthorized"),
    );
    const result = await changeLeadState(LEAD_ID, "REACHED_OUT");
    expect(result).toEqual({
      status: "error",
      message: "Your session expired. Please sign in again.",
    });
  });

  it("404 → says the lead is gone", async () => {
    vi.mocked(updateLeadState).mockRejectedValueOnce(new ApiError(404, "Not found", "not_found"));
    expect(await changeLeadState(LEAD_ID, "REACHED_OUT")).toEqual({
      status: "error",
      message: "That lead no longer exists.",
    });
  });

  it("an unknown failure → a generic message, never the raw detail", async () => {
    vi.mocked(updateLeadState).mockRejectedValueOnce(new Error("ECONNREFUSED 127.0.0.1:8000"));
    const result = await changeLeadState(LEAD_ID, "REACHED_OUT");
    expect(result).toEqual({
      status: "error",
      message: "Could not update the lead. Please try again.",
    });
  });

  it("a missing cookie short-circuits before the API is called", async () => {
    vi.mocked(getToken).mockResolvedValueOnce(null);
    const result = await changeLeadState(LEAD_ID, "REACHED_OUT");
    expect(result.status).toBe("error");
    expect(updateLeadState).not.toHaveBeenCalled();
  });

  it("a success reports ok", async () => {
    vi.mocked(updateLeadState).mockResolvedValueOnce({} as never);
    expect(await changeLeadState(LEAD_ID, "REACHED_OUT")).toEqual({
      status: "ok",
      message: "Updated.",
    });
  });
});

describe("assignToMe — assignment errors (FR10)", () => {
  it("422 → surfaces the API's reason (e.g. the assignee is not on the roster)", async () => {
    vi.mocked(assignLead).mockRejectedValueOnce(
      new ApiError(422, "assignee is not a configured attorney", "validation_error"),
    );
    expect(await assignToMe(LEAD_ID)).toEqual({
      status: "error",
      message: "assignee is not a configured attorney",
    });
  });

  it("anything else → a generic message", async () => {
    vi.mocked(assignLead).mockRejectedValueOnce(new ApiError(500, "kaboom", "server_error"));
    expect(await assignToMe(LEAD_ID)).toEqual({
      status: "error",
      message: "Could not assign the lead. Please try again.",
    });
  });

  it("assigns to the subject of the caller's own token, never a form value", async () => {
    vi.mocked(assignLead).mockResolvedValueOnce({} as never);
    const result = await assignToMe(LEAD_ID);
    expect(result.status).toBe("ok");
    expect(vi.mocked(assignLead).mock.calls[0][2]).toBe("attorney@example.com");
  });
});

describe("status portal — lookup errors (EXT1)", () => {
  it("404 → a not-found message that leaks nothing", async () => {
    vi.mocked(trackLead).mockRejectedValueOnce(new ApiError(404, "Not found", "not_found"));
    const form = new FormData();
    form.set("code", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA");
    const state = await lookupStatus({}, form);
    expect(state.error).toMatch(/could not find a submission with that code/i);
    expect(state.status).toBeUndefined();
  });

  it("429 → asks the visitor to wait", async () => {
    vi.mocked(trackLead).mockRejectedValueOnce(new ApiError(429, "slow down", "rate_limited"));
    const form = new FormData();
    form.set("code", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA");
    expect((await lookupStatus({}, form)).error).toMatch(/too many lookups/i);
  });

  it("an empty code never reaches the API", async () => {
    const form = new FormData();
    form.set("code", "   ");
    const state = await lookupStatus({}, form);
    expect(state.error).toMatch(/enter the tracking code/i);
    expect(trackLead).not.toHaveBeenCalled();
  });

  it("an unknown failure → a generic message", async () => {
    vi.mocked(trackLead).mockRejectedValueOnce(new Error("socket hang up"));
    const form = new FormData();
    form.set("code", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA");
    expect((await lookupStatus({}, form)).error).toBe(
      "Something went wrong looking that up. Please try again.",
    );
  });
});
