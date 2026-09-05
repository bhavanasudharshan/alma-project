import { expect, test, type Page } from "@playwright/test";
import path from "node:path";

/**
 * End-to-end coverage: the whole product through a real browser.
 *
 * One file on purpose, run serially (see playwright.config.ts): the specs share one
 * API and one throwaway SQLite database, and the first of them is a single linear
 * journey rather than isolated cases. Everything here uses placeholder identities --
 * no personal data in fixtures.
 */

const ATTORNEY_EMAIL = process.env.E2E_ATTORNEY_EMAIL ?? "attorney@example.com";
const ATTORNEY_PASSWORD = process.env.E2E_ATTORNEY_PASSWORD ?? "changeme";
// The roster injected by playwright.config.ts: the first entry is ATTORNEY_EMAIL.
const ATTORNEY_NAME = process.env.E2E_ATTORNEY_NAME ?? "Alex Chen";
const SECOND_EMAIL = process.env.E2E_SECOND_ATTORNEY_EMAIL ?? "sam@example.com";
const SECOND_NAME = process.env.E2E_SECOND_ATTORNEY_NAME ?? "Sam Reyes";
const RESUME = path.join(__dirname, "fixtures", "resume.pdf");
const NOT_A_RESUME = path.join(__dirname, "fixtures", "notes.txt");

type Applicant = { firstName: string; lastName: string; email: string };

/** Unique per run so repeated runs against one database stay distinguishable. */
function uniqueApplicant(): Applicant {
  const stamp = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  return { firstName: `Ada${stamp}`, lastName: "Lovelace", email: `ada${stamp}@example.com` };
}

/** Submit the public form and land on the thank-you page (FR1). */
async function apply(page: Page, applicant: Applicant) {
  await page.goto("/apply");
  await page.getByLabel("First name").fill(applicant.firstName);
  await page.getByLabel("Last name").fill(applicant.lastName);
  await page.getByLabel("Email").fill(applicant.email);
  // The file input is visually hidden behind a styled label (design pass), and two
  // labels point at it, so target the control by id rather than by accessible name.
  await page.locator("input#resume").setInputFiles(RESUME);
  await page.getByRole("button", { name: "Submit application" }).click();
  await expect(page).toHaveURL(/\/thank-you$/);
}

/** Sign in through the real login form and end up at the queue (FR4). */
async function signIn(page: Page, email: string, password = ATTORNEY_PASSWORD) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/leads/);
}

/**
 * The tracking code for a submission, read from the throwaway e2e database.
 *
 * The code is deliberately never rendered in the UI or returned by the API -- it only
 * reaches the applicant by email (EXT1) -- so a browser test cannot obtain one any
 * other way. Reading the e2e SQLite file is the narrowest way to prove the happy path.
 * `node:sqlite` is typed only in @types/node 22+, hence the cast.
 */
async function trackingCodeFor(email: string): Promise<string> {
  type Sqlite = {
    DatabaseSync: new (
      file: string,
      options?: { readOnly?: boolean },
    ) => {
      prepare(sql: string): { get(...params: unknown[]): { tracking_code?: string } | undefined };
      close(): void;
    };
  };
  const specifier = "node:sqlite";
  const { DatabaseSync } = (await import(specifier)) as unknown as Sqlite;

  const url = process.env.E2E_DATABASE_URL ?? "sqlite:///./data/e2e.db";
  // The API resolves a relative sqlite path against the repo root, so we do too.
  const relative = url.replace(/^sqlite:\/\/\/\.?\/?/, "");
  const db = new DatabaseSync(path.join(__dirname, "..", "..", relative), { readOnly: true });
  try {
    const row = db.prepare("SELECT tracking_code FROM leads WHERE email = ?").get(email);
    expect(row?.tracking_code, `no lead stored for ${email}`).toBeTruthy();
    return row!.tracking_code!;
  } finally {
    db.close();
  }
}

test("a lead can apply, and an attorney can find, claim and progress them", async ({ page }) => {
  const applicant = uniqueApplicant();

  await test.step("submit the public form", async () => {
    await apply(page, applicant);
    await expect(
      page.getByRole("heading", { name: /we've received your application/i }),
    ).toBeVisible();
  });

  await test.step("the thank-you page offers the status portal", async () => {
    await page.getByRole("link", { name: "Check status" }).click();
    await expect(page).toHaveURL(/\/status$/);
    await expect(page.getByLabel("Tracking code")).toBeVisible();
  });

  await test.step("signing in is required to reach the queue", async () => {
    await page.goto("/leads");
    await expect(page).toHaveURL(/\/login\?next=%2Fleads/);

    await page.getByLabel("Email").fill(ATTORNEY_EMAIL);
    await page.getByLabel("Password").fill(ATTORNEY_PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page).toHaveURL(/\/leads/);
  });

  const row = () => page.getByRole("row").filter({ hasText: applicant.email });

  await test.step("the new lead is in the queue as PENDING and already owned (FR10)", async () => {
      await expect(row()).toBeVisible();
      await expect(row().getByText("Pending")).toBeVisible();

      // Auto-assignment: a submission never sits ownerless, so the roster display name
      // is there from the start and there is nothing left to claim.
      await expect(row()).toContainText(ATTORNEY_NAME);
      await expect(row().getByRole("button", { name: "Assign to me" })).toHaveCount(0);
    });

    await test.step("the Mine tab shows only this attorney's leads", async () => {
    await page.getByRole("link", { name: "Mine", exact: true }).click();
    await expect(row()).toBeVisible();

    await page.getByRole("link", { name: "Unassigned", exact: true }).click();
    await expect(row()).toHaveCount(0);

    await page.getByRole("link", { name: "All", exact: true }).click();
  });

  await test.step("marking reached out flips the badge and retires the button", async () => {
    await row().getByRole("button", { name: "Mark reached out" }).click();

    await expect(row().getByText("Reached out")).toBeVisible();
    await expect(row().getByRole("button", { name: "Mark reached out" })).toHaveCount(0);
  });

  await test.step("the pipeline continues to QUALIFIED", async () => {
    await row().getByRole("button", { name: "Mark qualified" }).click();

    await expect(row().getByText("Qualified")).toBeVisible();
    await expect(row().getByRole("button", { name: "Mark qualified" })).toHaveCount(0);
  });

  await test.step("the filter tabs reflect the new state", async () => {
    await page.getByRole("link", { name: "Pending", exact: true }).click();
    await expect(row()).toHaveCount(0);

    await page.getByRole("link", { name: "Reached out", exact: true }).click();
    await expect(row()).toHaveCount(0);

    await page.getByRole("link", { name: "Qualified", exact: true }).click();
    await expect(row()).toBeVisible();
  });
});

test("a submission with the honeypot filled still reaches the confirmation page", async ({
  page,
}) => {
  // Regression for NOTES.md #17: Chrome address autofill filled the hidden field for
  // real applicants, and the API's bodiless 202 then crashed the client with
  // "Unexpected end of JSON input". The applicant must see exactly what everyone else
  // sees — the silent drop has to stay silent.
  const applicant = uniqueApplicant();

  await page.goto("/apply");
  await page.getByLabel("First name").fill(applicant.firstName);
  await page.getByLabel("Last name").fill(applicant.lastName);
  await page.getByLabel("Email").fill(applicant.email);
  await page.locator("input#resume").setInputFiles(RESUME);
  // Stand in for autofill reaching the hidden field.
  await page.locator("input#contact_ref_2").fill("https://spam.example");

  await page.getByRole("button", { name: "Submit application" }).click();

  await expect(page).toHaveURL(/\/thank-you$/);
  await expect(
    page.getByRole("heading", { name: /we've received your application/i }),
  ).toBeVisible();
});

test("a repeat transition from a stale tab is a calm notice, not an error (FR8)", async ({
  page,
}) => {
  const applicant = uniqueApplicant();
  await apply(page, applicant);
  await signIn(page, ATTORNEY_EMAIL);

  const row = (p: Page) => p.getByRole("row").filter({ hasText: applicant.email });

  // A second tab holding a now-stale view of the same lead.
  const stale = await page.context().newPage();
  await stale.goto("/leads");
  await expect(stale.locator("body")).toBeVisible();
  const staleButton = row(stale).getByRole("button", { name: "Mark reached out" });
  await expect(staleButton).toBeVisible();

  // The first tab wins the race.
  await row(page).getByRole("button", { name: "Mark reached out" }).click();
  await expect(row(page).getByText("Reached out")).toBeVisible();

  // The loser gets the API's `already_in_state` 409, shown as a neutral notice.
  await staleButton.click();
  await expect(row(stale).getByText(/already in that state/i)).toBeVisible();
  await expect(stale.getByText(/could not update/i)).toHaveCount(0);

  await stale.close();
});

test("the public form reports its own validation errors before anything is sent (FR1)", async ({
  page,
}) => {
  await page.goto("/apply");

  await test.step("an empty submit names every required field", async () => {
    await page.getByRole("button", { name: "Submit application" }).click();
    await expect(page).toHaveURL(/\/apply$/);
    await expect(page.locator("#first_name-error")).toContainText("First name is required");
    await expect(page.locator("#last_name-error")).toContainText("Last name is required");
    await expect(page.locator("#email-error")).toContainText("Email is required");
    await expect(page.locator("#resume-error")).toContainText(/attach your cv or resume/i);
  });

  await test.step("a malformed email is caught", async () => {
    await page.getByLabel("Email").fill("not-an-email");
    await page.getByRole("button", { name: "Submit application" }).click();
    await expect(page.locator("#email-error")).toContainText("Enter a valid email address");
  });

  await test.step("a file outside the allow-list is refused (S2/SEC2b)", async () => {
    const applicant = uniqueApplicant();
    await page.getByLabel("First name").fill(applicant.firstName);
    await page.getByLabel("Last name").fill(applicant.lastName);
    await page.getByLabel("Email").fill(applicant.email);
    await page.locator("input#resume").setInputFiles(NOT_A_RESUME);
    await page.getByRole("button", { name: "Submit application" }).click();

    await expect(page.locator("#resume-error")).toContainText("Upload a PDF or DOCX file");
    await expect(page).toHaveURL(/\/apply$/);
  });
});

test("the queue is closed to anyone without a session (S1/FR4)", async ({ page }) => {
  await test.step("an unauthenticated visit redirects to login and remembers where", async () => {
    await page.goto("/leads?state=PENDING");
    await expect(page).toHaveURL(/\/login\?next=/);
    expect(new URL(page.url()).searchParams.get("next")).toBe("/leads?state=PENDING");
  });

  await test.step("a wrong password is refused inline, with no session created", async () => {
    await page.getByLabel("Email").fill(ATTORNEY_EMAIL);
    await page.getByLabel("Password").fill("definitely-not-the-password");
    await page.getByRole("button", { name: "Sign in" }).click();

    // Scope to the form's own alert: getByRole("alert") also matches Next's route announcer.
    await expect(page.locator('form p[role="alert"]')).toContainText(
      /incorrect|invalid|credential/i,
    );
    await expect(page).toHaveURL(/\/login/);
    expect(await page.context().cookies()).not.toContainEqual(
      expect.objectContaining({ name: "alma_token" }),
    );
  });
});

test("the status portal shows a real submission and refuses an unknown code (EXT1)", async ({
  page,
}) => {
  const applicant = uniqueApplicant();
  await apply(page, applicant);
  const code = await trackingCodeFor(applicant.email);

  await test.step("a valid code returns the state and the timeline", async () => {
    await page.goto("/status");
    await page.getByLabel("Tracking code").fill(code);
    await page.getByRole("button", { name: "Check status" }).click();

    await expect(page.getByRole("heading", { name: "Timeline" })).toBeVisible();
    await expect(page.getByText("Pending").first()).toBeVisible();
    // EXT1: the prospect sees state and dates only -- never their own PII echoed back.
    await expect(page.getByText(applicant.email)).toHaveCount(0);
  });

  await test.step("a bogus code says nothing beyond 'not found'", async () => {
    await page.goto("/status");
    await page.getByLabel("Tracking code").fill("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA");
    await page.getByRole("button", { name: "Check status" }).click();

    // Target the field error by id: getByRole("alert") also matches Next's route announcer.
    await expect(page.locator("#code-error")).toContainText(/could not find a submission/i);
    await expect(page.getByRole("heading", { name: "Timeline" })).toHaveCount(0);
  });
});

test("a released lead can be claimed, and Mine is per-attorney (FR10)", async ({
  page,
  request,
}) => {
  // Submissions are auto-assigned, so to exercise the manual "Assign to me" path this
  // first releases one through the API — which is also the only way to reassign in this
  // build. Which attorney the balancer picked does not matter: the lead is released and
  // then deliberately claimed, so the assertions do not depend on earlier specs' load.
  const applicant = uniqueApplicant();
  await apply(page, applicant);

  const api = process.env.E2E_API_URL ?? "http://localhost:8000";

  const token = await test.step("get an API token for the second attorney", async () => {
    const response = await request.post(`${api}/api/v1/auth/login`, {
      data: { email: SECOND_EMAIL, password: ATTORNEY_PASSWORD },
    });
    expect(response.status()).toBe(200);
    return (await response.json()).access_token as string;
  });

  await test.step("release the lead back to the unassigned pool", async () => {
    const list = await request.get(`${api}/api/v1/leads?limit=200`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const { items } = await list.json();
    const lead = items.find((l: { email: string }) => l.email === applicant.email);
    expect(lead, "the submitted lead should be in the queue").toBeTruthy();

    const cleared = await request.patch(`${api}/api/v1/leads/${lead.id}/assign`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { assignee: null },
    });
    expect(cleared.status()).toBe(200);
    expect((await cleared.json()).assigned_to).toBeNull();
  });

  const row = () => page.getByRole("row").filter({ hasText: applicant.email });

  await test.step("the second attorney claims it from the Unassigned tab", async () => {
    await signIn(page, SECOND_EMAIL);
    await page.getByRole("link", { name: "Unassigned", exact: true }).click();

    await expect(row().getByRole("button", { name: "Assign to me" })).toBeVisible();
    await row().getByRole("button", { name: "Assign to me" }).click();

    // The server action revalidates /leads, so the claimed lead leaves this filter.
    // Waiting for that is what makes the next navigation race-free.
    await expect(row()).toHaveCount(0);

    await page.getByRole("link", { name: "All", exact: true }).click();
    await expect(row()).toContainText(SECOND_NAME);
    await expect(row()).not.toContainText(ATTORNEY_NAME);
  });

  await test.step("their Mine holds it; Unassigned no longer does", async () => {
    await page.getByRole("link", { name: "Mine", exact: true }).click();
    await expect(row()).toBeVisible();

    await page.getByRole("link", { name: "Unassigned", exact: true }).click();
    await expect(row()).toHaveCount(0);
  });

  await test.step("the other attorney's Mine does not show it", async () => {
    await page.getByRole("button", { name: "Log out" }).click();
    await expect(page).toHaveURL(/\/login/);

    await signIn(page, ATTORNEY_EMAIL);
    await page.getByRole("link", { name: "Mine", exact: true }).click();
    await expect(row()).toHaveCount(0);

    await page.getByRole("link", { name: "All", exact: true }).click();
    await expect(row()).toContainText(SECOND_NAME);
  });
});
