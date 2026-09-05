import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

/**
 * Unit tests for the web layer.
 *
 * Node environment on purpose: everything under test is pure (schemas, tables, error
 * mapping, cookie flags), so there is no DOM to boot and no extra dependency to add.
 * `include` is narrowed to `tests/` so Vitest never picks up the Playwright specs in
 * `e2e/`, which use their own runner.
 */
export default defineConfig({
  test: {
    include: ["tests/**/*.test.ts"],
    environment: "node",
    coverage: { include: ["lib/**/*.ts"], reporter: ["text-summary"] },
  },
  resolve: {
    alias: { "@": fileURLToPath(new URL(".", import.meta.url)) },
  },
});
