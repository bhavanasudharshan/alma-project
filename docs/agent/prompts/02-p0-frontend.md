# Prompt 02 — P0 frontend: public apply form, login, guarded leads table

> **Role reminder**: you are Claude Code, the implementer and tester. This prompt comes from the planning session (architect / product owner / QA lead), which never writes code. Scope, acceptance criteria and architecture are fixed here; implement them, test them, report back. Put any disagreement under "Questions for the architect" in your report — do not act on it.

Read `CLAUDE.md`, `docs/PLAN.md` §2/§4 (P0), and the API section of `README.md` for the contract. Stage is P0. Work only in `web/`.

## Build
1. **`/apply`** (public, `app/(public)/apply/page.tsx`): form with first name, last name, email, resume (accept `.pdf,.doc,.docx`). Client-side validation with zod + react-hook-form (install both). Submit via a server action that forwards multipart to `POST /api/v1/leads` and maps API errors (422/413/415) to field or form-level messages. On success redirect to `/thank-you` with a short confirmation. Accessible labels, disabled state while submitting.
2. **`/login`** (`app/(internal)/login/page.tsx`): email + password → `POST /app/api/auth/login/route.ts` (Next route handler) which calls the FastAPI login and sets an `httpOnly`, `sameSite=lax`, `secure` in prod cookie `alma_token`. `POST /app/api/auth/logout` clears it. Wrong creds → inline error.
3. **`middleware.ts`**: redirect any `/leads*` request without the cookie to `/login?next=…`.
4. **`/leads`** (`app/(internal)/leads/page.tsx`, server component): read cookie, call `GET /api/v1/leads` with Bearer. Table columns: name, email, submitted (relative + absolute), state badge, resume (link to a Next route handler `app/api/leads/[id]/resume/route.ts` that proxies the authenticated API stream so the token never reaches the client), action. Filter tabs `Pending | Reached out | All` via `?state=`. Pagination controls. Empty state.
5. **Mark reached out**: server action calling `PATCH /api/v1/leads/{id}/state`, then `revalidatePath('/leads')`. Button only rendered for `PENDING`. Surface 409/other errors with a toast or inline message, not a crash.
6. **Layout/nav**: internal layout shows attorney email (decode JWT `sub` server-side) and Logout. Public layout minimal with the Alma-style wordmark text (no real logo asset).
7. **`lib/api.ts`**: typed helpers (`createLead`, `login`, `listLeads`, `updateLeadState`) with TS types mirroring the API schemas. Handle non-2xx uniformly.
8. Styling: Tailwind only, clean and readable; no component library.
9. `pnpm lint`, `pnpm tsc --noEmit` clean; `make lint` green.
10. Manual E2E: start `make dev`, run through apply → login → list → mark reached out → filter. Paste what you observed. Then commit: `feat(web): public apply form, attorney login, guarded leads table` with trailers (`Stage: P0`). Update `NOTES.md`.

## Constraints
Do not modify `api/` except to fix a genuine contract bug — if you do, say so explicitly in the report and make it a separate commit. Do not push.

## Report back
Route list, where the token lives and why, anything in the API contract that was awkward from the client side.
End with a section **Questions for the architect** (write "none" if none).
