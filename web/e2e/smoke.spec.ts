import { expect, test } from "@playwright/test";
import path from "node:path";

/**
 * End-to-end smoke: the whole product in one pass.
 *
 * apply → thank-you → status portal → login → queue → mark reached out → badge flips.
 * This is the only test that exercises the browser, the Next server and the API
 * together, so it is deliberately one linear journey rather than isolated cases.
 */

const ATTORNEY_EMAIL = process.env.E2E_ATTORNEY_EMAIL ?? "attorney@example.com";
const ATTORNEY_PASSWORD = process.env.E2E_ATTORNEY_PASSWORD ?? "changeme";
const RESUME = path.join(__dirname, "fixtures", "resume.pdf");

/** Unique per run so repeated runs against one database stay distinguishable. */
function uniqueApplicant() {
  const stamp = Date.now();
  return { firstName: `Ada${stamp}`, lastName: "Lovelace", email: `ada${stamp}@example.com` };
}

test("a lead can apply, and an attorney can find and progress them", async ({ page }) => {
  const applicant = uniqueApplicant();

  await test.step("submit the public form", async () => {
    await page.goto("/apply");
    await page.getByLabel("First name").fill(applicant.firstName);
    await page.getByLabel("Last name").fill(applicant.lastName);
    await page.getByLabel("Email").fill(applicant.email);
    // The file input is visually hidden behind a styled label (design pass), and two
    // labels point at it, so target the control by id rather than by accessible name.
    await page.locator("input#resume").setInputFiles(RESUME);
    await page.getByRole("button", { name: "Submit application" }).click();

    await expect(page).toHaveURL(/\/thank-you$/);
    await expect(page.getByRole("heading", { name: /we've received your application/i })).toBeVisible();
  });

  await test.step("the thank-you page offers the status portal", async () => {
    await page.getByRole("link", { name: "Check status" }).click();
    await expect(page).toHaveURL(/\/status$/);
    await expect(page.getByLabel("Tracking code")).toBeVisible();
  });

  await test.step("signing in is required to reach the queue", async () => {
    await page.goto("/leads");
    await expect(page).toHaveURL(/\/login/);

    await page.getByLabel("Email").fill(ATTORNEY_EMAIL);
    await page.getByLabel("Password").fill(ATTORNEY_PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page).toHaveURL(/\/leads/);
  });

  const row = () => page.getByRole("row").filter({ hasText: applicant.email });

  await test.step("the new lead is in the queue as PENDING", async () => {
    await expect(row()).toBeVisible();
    await expect(row().getByText("Pending")).toBeVisible();
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

test("the status portal rejects an unknown tracking code without leaking anything", async ({
  page,
}) => {
  await page.goto("/status");
  await page.getByLabel("Tracking code").fill("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA");
  await page.getByRole("button", { name: "Check status" }).click();

  // Target the field error by id: getByRole("alert") also matches Next's route announcer.
  await expect(page.locator("#code-error")).toContainText(/could not find a submission/i);
});
