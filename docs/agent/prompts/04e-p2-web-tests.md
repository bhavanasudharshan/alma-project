# Prompt 04e — P2: web test suite (unit + E2E), quick and complete

> **Role reminder**: you are Claude Code, tester. No product code changes except what a failing test proves is a bug (report it, fix it, name it in NOTES.md). Time box: 20 min. No commits.

## Unit tests — Vitest (one dev dependency; `pnpm test`)
1. `lib/validation.ts`: each required field rejects empty/whitespace; email format; résumé type allow-list (`.pdf`, `.docx` accepted; `.doc`, `.exe`, `.pdf.exe` rejected); size limit at exactly 5 MB and 5 MB + 1 byte; honeypot field ignored by validation.
2. `lib/lead-actions.ts` (NEXT_ACTION table): every `LeadState` — PENDING, REACHED_OUT, QUALIFIED — resolves to an action or an explicit `null`; never `undefined` (this is the regression test for NOTES.md mistake #15).
3. Error mapping: API `409 already_in_state` → calm notice; `409 invalid_transition` → error; `413`/`415`/`422` → field or form-level messages; unknown → generic.
4. Auth helpers: cookie name/flags builder produces `HttpOnly; SameSite=Lax; Path=/` and `Secure` only when not local.
Keep tests pure (no network, no DOM beyond what a helper needs).

## E2E — Playwright (extend `web/e2e/smoke.spec.ts`, keep one file, keep it fast)
5. Existing: apply → thank-you → login → mark reached out → badge flips.
6. Add: validation errors shown for empty submit and wrong file type; `/leads` unauthenticated → redirect to `/login?next=`; wrong password → inline error; status portal: valid code → state + timeline, bogus code → not-found message; second attorney login (from the roster) → "Assign to me" → name appears in the Assigned-to column → "Mine" tab shows only that lead; `QUALIFIED` transition via UI; repeat action → calm notice, not an error.
7. Use the throwaway e2e database and seeded roster; no personal data in fixtures.

## Wire-up
- `make test` runs pytest **and** `pnpm test`; `make e2e` unchanged; CI web job runs `pnpm test`; e2e job already exists.
- Paste: unit test count and runtime, Playwright pass count and runtime (run twice), coverage of `lib/` if Vitest reports it.

## Report back
Counts, any bug found, proposed commit `test(web): unit tests and extended e2e coverage`, "Questions for the architect".
