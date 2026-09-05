"use server";

/** Server action for the public lead form. Runs on the server; no token involved. */

import { redirect } from "next/navigation";

import { ApiError, createLead } from "@/lib/api";
import { leadFormSchema } from "@/lib/validation";

export type ApplyState = {
  /** Form-level message shown above the fields. */
  formError?: string;
  /** Field-level messages keyed by input name. */
  fieldErrors?: Partial<Record<"first_name" | "last_name" | "email" | "resume", string>>;
};

/** Map the API's error codes onto the field the applicant can actually fix (M6). */
function toState(error: ApiError): ApplyState {
  switch (error.code) {
    case "resume_too_large":
      return { fieldErrors: { resume: "Your file must be 5 MB or smaller." } };
    case "unsupported_media_type":
      return { fieldErrors: { resume: error.message } };
    case "validation_error": {
      // The API prefixes the field name: "email: value is not a valid email address".
      const [field, ...rest] = error.message.split(":");
      const key = field.trim() as keyof NonNullable<ApplyState["fieldErrors"]>;
      if (rest.length && ["first_name", "last_name", "email", "resume"].includes(key)) {
        return { fieldErrors: { [key]: rest.join(":").trim() } };
      }
      return { formError: error.message };
    }
    case "storage_unavailable":
      return {
        formError:
          "We could not store your file just now. Please try again in a moment — nothing was saved.",
      };
    default:
      return { formError: "Something went wrong submitting your application. Please try again." };
  }
}

export async function submitApplication(
  _previous: ApplyState,
  formData: FormData,
): Promise<ApplyState> {
  // Re-validate server-side: client checks are a convenience, not a guarantee.
  const parsed = leadFormSchema.safeParse({
    first_name: formData.get("first_name"),
    last_name: formData.get("last_name"),
    email: formData.get("email"),
    resume: formData.get("resume"),
  });

  if (!parsed.success) {
    const fieldErrors: ApplyState["fieldErrors"] = {};
    for (const issue of parsed.error.issues) {
      const key = issue.path[0] as keyof NonNullable<ApplyState["fieldErrors"]>;
      fieldErrors[key] ??= issue.message;
    }
    return { fieldErrors };
  }

  const payload = new FormData();
  // SEC4: forwarded untouched so the API decides; the client never judges a bot.
  payload.set("contact_ref_2", String(formData.get("contact_ref_2") ?? ""));
  payload.set("first_name", parsed.data.first_name);
  payload.set("last_name", parsed.data.last_name);
  payload.set("email", parsed.data.email);
  payload.set("resume", parsed.data.resume);

  try {
    // A 202 (honeypot tripped) resolves to null rather than throwing: the applicant
    // sees the same confirmation as everyone else, which is the point.
    await createLead(payload);
  } catch (error) {
    if (error instanceof ApiError) return toState(error);
    throw error;
  }

  // redirect() throws internally, so it must sit outside the try block.
  redirect("/thank-you");
}
