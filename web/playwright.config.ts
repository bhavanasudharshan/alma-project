import { defineConfig, devices } from "@playwright/test";

/**
 * E2E configuration.
 *
 * The servers are expected to be already running (`make dev`), or started by
 * `webServer` below when they are not — so `make e2e` works from a cold start and CI
 * does not need a bespoke boot script.
 */
const WEB_URL = process.env.E2E_WEB_URL ?? "http://localhost:3000";
const API_URL = process.env.E2E_API_URL ?? "http://localhost:8000";

export default defineConfig({
  testDir: "./e2e",
  // The smoke test walks one lead through the whole pipeline, so the specs inside a
  // file must not run in parallel with each other.
  fullyParallel: false,
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : [["list"]],
  timeout: 30_000,
  expect: { timeout: 10_000 },

  use: {
    baseURL: WEB_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },

  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],

  webServer: [
    {
      command: "uv run uvicorn app.main:app --port 8000",
      cwd: "../api",
      url: `${API_URL}/api/v1/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      env: {
        // Rate limits are per IP and the smoke test submits repeatedly across runs.
        RATE_LIMIT_ENABLED: "false",
        // A throwaway database: the smoke test must never write into, or depend on,
        // whatever the developer has in their dev database. `make e2e` deletes it first.
        DATABASE_URL: process.env.E2E_DATABASE_URL ?? "sqlite:///./data/e2e.db",
      },
    },
    {
      command: "pnpm dev --port 3000",
      url: WEB_URL,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
