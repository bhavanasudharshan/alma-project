# NOTES — attribution & agent log

Legend — **agent-generated**: written by Claude Code from a prompt, reviewed by me. **agent-assisted**: agent drafted, I materially edited. **hand-written**: written by me.

Planning and orchestration: Claude (Cowork session) with Bhavana — `docs/PLAN.md`, prompt pack, this file's skeleton, `CLAUDE.md`.
Implementation: Claude Code, one prompt per stage (`docs/agent/prompts/`), transcripts in `docs/agent/sessions/`.

## File attribution

| path | mode | stage | note |
|---|---|---|---|
| docs/PLAN.md | agent-assisted | S0 | drafted in Cowork planning session, decisions made by Bhavana |
| CLAUDE.md | agent-assisted | S0 | |
| NOTES.md | agent-assisted | S0 | |
| docs/agent/prompts/*.md | agent-assisted | S0 | |
| api/pyproject.toml | agent-generated | S0 | uv project, pinned dep set from prompt 00 |
| api/ruff.toml | agent-generated | S0 | line length 100, isort enabled |
| api/app/main.py | agent-generated | S0 | app factory, CORS from settings (S5) |
| api/app/core/config.py | agent-generated | S0 | pydantic-settings, reads repo-root .env (S3) |
| api/app/api/v1/__init__.py | agent-generated | S0 | v1 router aggregate |
| api/app/api/v1/health.py | agent-generated | S0 | GET /api/v1/health |
| api/app/db/base.py | agent-generated | S0 | DeclarativeBase for Alembic metadata (M3) |
| api/app/db/session.py | agent-generated | S0 | engine/session factory; SQLite URL anchored to repo root |
| api/alembic.ini | agent-generated | S0 | URL deliberately absent; env.py owns it (S3) |
| api/alembic/env.py | agent-generated | S0 | reads settings.database_url, batch mode for SQLite |
| api/alembic/script.py.mako | agent-generated | S0 | migration template |
| api/tests/test_health.py | agent-generated | S0 | Stage 0 smoke test (M2) |
| web/lib/api.ts | agent-generated | S0 | typed apiFetch + ApiError over NEXT_PUBLIC_API_URL |
| web/app/page.tsx | agent-generated | S0 | minimal landing page linking /apply and /leads |
| web/app/layout.tsx | agent-generated | S0 | trimmed create-next-app default (fonts removed) |
| web/app/globals.css | agent-generated | S0 | dropped dangling Geist font vars |
| Makefile | agent-generated | S0 | dev/api/web/test/lint/fmt/migrate/seed |
| .env.example | agent-generated | S0 | every Settings field documented (S3) |
| .gitignore | agent-generated | S0 | python, node, .env, data/, uploads/ |
| docker-compose.yml | agent-generated | S0 | profiles pg + s3, not wired to the app yet |
| README.md | agent-generated | S0 | skeleton with the 8 required headings |
| docs/DESIGN.md | agent-generated | S0 | headings only, filled at P2 |
| api/app/db/models/lead.py | agent-generated | P0 | Lead model, LeadState enum, indexes on state/created_at |
| api/alembic/versions/0001_leads.py | agent-generated | P0 | initial migration (M3) |
| api/app/schemas/lead.py | agent-generated | P0 | LeadCreate/LeadRead/List/StateUpdate; resume_key never exposed |
| api/app/schemas/auth.py | agent-generated | P0 | login + token models |
| api/app/repositories/lead_repo.py | agent-generated | P0 | create/get/list/update_state |
| api/app/services/exceptions.py | agent-generated | P0 | domain errors with stable codes (M6) |
| api/app/services/lead_state.py | agent-generated | P0 | single transition table (E1) |
| api/app/core/security.py | agent-generated | P2 | AttorneyDirectory holds a roster; constant-time verify |
| api/app/api/v1/leads.py | agent-generated | P2 | PATCH /assign, assigned_to filter, name resolution |
| api/alembic/versions/0003_assigned_to.py | agent-generated | P2 | assigned_to + event assignee columns |
| api/tests/test_assignment.py | agent-generated | P2 | 18 tests: roster login, assign, filters, no password leak |
| web/components/assign-to-me-button.tsx | agent-generated | P2 | claims a lead for the signed-in attorney |
| api/tests/test_state_concurrency.py | agent-generated | P0 | R2 regression barrier: 5×12 parallel PATCH + deterministic SQL-predicate test |
| api/app/repositories/lead_repo.py | agent-generated | P0 | update_state moved to a SQL predicate (race fix) |
| api/app/services/lead_service.py | agent-generated | P0 | intake use cases, upload validation, email scheduling (R1) |
| api/app/services/storage/base.py | agent-generated | P0 | FileStorage Protocol (E2) |
| api/app/services/storage/local.py | agent-generated | P0 | LocalDiskStorage, path-traversal safe (S2) |
| api/app/services/email/base.py | agent-generated | P0 | EmailService Protocol (E2) |
| api/app/services/email/console.py | agent-generated | P0 | console adapter, P0 default |
| api/app/services/email/messages.py | agent-generated | P0 | prospect + attorney bodies (FR2/FR3) |
| api/app/core/security.py | agent-generated | P0 | bcrypt hashing, JWT issue/decode, AttorneyDirectory (S4) |
| api/app/core/deps.py | agent-generated | P0 | adapter selection + current_attorney (M4/S1) |
| api/app/core/config.py | agent-generated | P0 | rewritten: full config surface per architect answer 1 |
| api/app/api/errors.py | agent-generated | P0 | global handlers, {detail, code} envelope (M6) |
| api/app/api/v1/auth.py | agent-generated | P0 | POST /auth/login |
| api/app/api/v1/leads.py | agent-generated | P0 | the five lead routes |
| api/app/main.py | agent-generated | P0 | registers handlers, warns on placeholder creds |
| api/tests/conftest.py | agent-generated | P0 | temp SQLite + fake adapters per test |
| api/tests/fakes.py | agent-generated | P0 | FakeStorage, FailingStorage, FakeEmailService |
| api/tests/test_leads_create.py | agent-generated | P0 | FR1/FR2/FR3/FR7, S2 upload limits |
| api/tests/test_auth.py | agent-generated | P0 | FR4, S1 route guard, S4 |
| api/tests/test_leads_list.py | agent-generated | P0 | FR5 filter + pagination |
| api/tests/test_state_transitions.py | agent-generated | P0 | FR8/FR9, E1 |
| api/tests/test_resume_download.py | agent-generated | P0 | FR6, S2 traversal, A1 |
| README.md | agent-generated | P0 | API table + curl walkthrough |
| .env.example | agent-generated | P0 | full config surface documented |
| web/lib/api.ts | agent-generated | P0 | typed client: createLead/login/listLeads/updateLeadState/fetchResume |
| web/lib/auth.ts | agent-generated | P0 | httpOnly cookie helpers; unverified sub decode for display only (S1) |
| web/lib/validation.ts | agent-generated | P0 | shared zod rules; client FileList vs server File |
| web/lib/format.ts | agent-generated | P0 | relative + absolute timestamps |
| web/middleware.ts | agent-generated | P0 | guards /leads*, preserves ?next= |
| web/app/(public)/layout.tsx | agent-generated | P0 | public chrome, wordmark only |
| web/app/(public)/apply/page.tsx | agent-generated | P0 | public form page (FR1) |
| web/app/(public)/apply/apply-form.tsx | agent-generated | P0 | RHF + zodResolver client validation |
| web/app/(public)/apply/actions.ts | agent-generated | P0 | server action; maps 422/413/415 to fields |
| web/app/(public)/thank-you/page.tsx | agent-generated | P0 | confirmation |
| web/app/(internal)/login/page.tsx | agent-generated | P0 | attorney sign-in, open-redirect-safe ?next |
| web/app/(internal)/login/login-form.tsx | agent-generated | P0 | posts to the cookie route handler |
| web/app/(internal)/leads/layout.tsx | agent-generated | P0 | internal chrome, attorney email, logout |
| web/app/(internal)/leads/page.tsx | agent-generated | P0 | queue: filters, pagination, badges (FR5) |
| web/app/(internal)/leads/actions.ts | agent-generated | P0 | markReachedOut; 409 => already-in-state |
| web/app/api/auth/login/route.ts | agent-generated | P0 | sets httpOnly alma_token (S1) |
| web/app/api/auth/logout/route.ts | agent-generated | P0 | clears the cookie |
| web/app/api/leads/[id]/resume/route.ts | agent-generated | P0 | streams the resume; token stays server-side |
| web/components/state-badge.tsx | agent-generated | P0 | state pill |
| web/components/mark-reached-out.tsx | agent-generated | P0 | calm notice on 409 |
| web/components/logout-button.tsx | agent-generated | P0 | |
| web/components/field-error.tsx | agent-generated | P0 | aria-describedby error text |
| api/app/services/storage/s3.py | agent-generated | P1 | S3/MinIO adapter, ensure_bucket, presigned_url |
| api/app/services/email/resend.py | agent-generated | P1 | Resend adapter; provider errors logged not raised |
| api/app/services/email/messages.py | agent-generated | P1 | LeadSnapshot + Jinja2 autoescape + CRLF-safe subjects |
| api/app/services/email/templates/*.j2 | agent-generated | P1 | HTML bodies with text fallback |
| api/app/services/email/console.py | agent-generated | P1 | INFO = recipient+subject+lead id; body at DEBUG (C1) |
| api/app/services/lead_state.py | agent-generated | P1 | TransitionRule(notify_prospect); AlreadyInState split |
| api/app/services/lead_service.py | agent-generated | P1 | magic-byte sniffing, tracking code, audit events |
| api/app/core/logging.py | agent-generated | P1 | request-id context + JSON toggle (M5) |
| api/app/core/limiter.py | agent-generated | P1 | slowapi per-IP limits (SEC1) |
| api/app/api/middleware.py | agent-generated | P1 | request-id + security headers (SEC6) |
| api/app/api/v1/health.py | agent-generated | P1 | health now checks the database (M5) |
| api/alembic/versions/0002_events_tracking.py | agent-generated | P1 | lead_events + tracking_code with backfill |
| api/tests/test_storage_s3.py | agent-generated | P1 | moto round trip |
| api/tests/test_email_templates.py | agent-generated | P1 | field coverage + XSS/CRLF escaping |
| api/tests/test_rate_limit.py | agent-generated | P1 | 6th submission 429, Retry-After |
| api/tests/test_hardening.py | agent-generated | P1 | SEC2/SEC4/SEC6/SEC9/EXT1 |
| api/tests/test_startup_guard.py | agent-generated | P1 | hard-fail on placeholder secrets |
| api/tests/test_console_email_privacy.py | agent-generated | P1 | PII stays out of INFO logs |
| .github/workflows/ci.yml | agent-generated | P1/P2 | api, api-postgres, web, e2e jobs |
| api/app/api/v1/leads.py | agent-generated | P2 | public /leads/track/{code}; notify hook on transition |
| api/app/services/lead_service.py | agent-generated | P2 | public_status, StateChange, send_status_change_email |
| api/app/services/email/templates/status_changed.html.j2 | agent-generated | P2 | EXT2 prospect update |
| api/tests/test_status_portal.py | agent-generated | P2 | EXT1: 8 tests incl. no-PII assertions |
| api/tests/test_status_notifications.py | agent-generated | P2 | EXT2: 7 tests incl. no re-notify on 409 |
| web/app/(public)/status/* | agent-generated | P2 | public status portal page + action |
| web/lib/lead-actions.ts | agent-generated | P2 | NEXT_ACTION table (plain module, see mistake #15) |
| web/components/state-action-button.tsx | agent-generated | P2 | generic transition button (was mark-reached-out) |
| web/e2e/smoke.spec.ts | agent-generated | P2 | Playwright: apply -> status -> login -> REACHED_OUT -> QUALIFIED |
| web/playwright.config.ts | agent-generated | P2 | boots both servers, rate limits off |

| web/next.config.ts | agent-generated | P1 | CSP and security headers (SEC6) |
| web/vitest.config.mts | agent-generated | P2 | vitest wiring, node env, lib/ coverage target |
| web/tests/validation.test.ts | agent-generated | P2 | 43 tests: field rules, résumé allow-list, size bounds |
| web/tests/error-mapping.test.ts | agent-generated | P2 | 17 tests: server actions map API codes to user-facing state |
| web/tests/lead-actions.test.ts | agent-generated | P2 | 10 tests: NEXT_ACTION totality — the #15 regression barrier |
| web/tests/auth.test.ts | agent-generated | P2 | 13 tests: cookie flags, Secure in prod, claim decoding |
| web/e2e/fixtures/notes.txt | agent-generated | P2 | wrong-type upload fixture |
| api/tests/test_auto_assignment.py | agent-generated | P2 | 10 tests: least-loaded pick, CC/Reply-To, empty-roster fallback |
| api/tests/test_seed_script.py | agent-generated | P2 | 5 tests: seed never sends email, refuses outside local |
| docs/DESIGN.md | agent-generated | P2 | written by a subagent against the code as built |
| docs/PRODUCT_GUIDE.md | agent-generated | P2 | screenshot walkthrough |
| web/package.json | agent-generated | P0 | pnpm override postcss ^8.5.23 — patches 4 advisories (audit 01b C11) |
| api/app/schemas/auth.py | agent-generated | P0 | noqa S105 on token_type (audit 01b C9) |
| .gitignore | agent-generated | P0 | added docs/private/ + sessions/*.raw.md per CLAUDE.md privacy |

## Agent mistakes caught (candidates for AGENT_USAGE.md — fill in as they happen, never retroactively)

| # | stage | what the agent produced | how it was caught | fix |
|---|---|---|---|---|
| 1 | S0 | `pnpm create next-app@latest` installed Next.js 16.3.4 | caught while verifying the scaffold against the fixed stack in CLAUDE.md ("Next.js 15", do not substitute) | re-scaffolded with `create-next-app@15`; `web/` now pins next 15.5.25 |
| 2 | S0 | removed the Geist font imports from `layout.tsx` but left `--font-geist-sans` / `--font-geist-mono` referenced in `globals.css` | self-review of the diff before running the gates; lint does not catch a dangling CSS custom property | dropped both vars and set an explicit system font stack |
| 3 | P0 | built `LeadCreate` by hand inside the router, so a bad email raised a raw pydantic `ValidationError` and returned **500** instead of 422 | `test_invalid_email_returns_422` and `test_blank_first_name_returns_422` failed on the first run of the suite | re-raise as `RequestValidationError` so multipart fields get the same 422 envelope as JSON bodies |
| 4 | P0 | `sanitise_filename` did not treat `\\` as a separator, so a Windows-style path was mangled rather than flattened | parametrised traversal test disagreed with the implementation | normalise `\\` to `/` before taking the basename; `..\\..\\windows\\system32` now yields `system32` |
| 5 | P0 | assumed a UTC datetime serialises as `+00:00`; pydantic emits `Z` | the assertion I had just written failed | corrected the test, not the code — both are valid ISO 8601 |
| 6 | P0 | **HEADLINE — lost-update race on `PATCH /leads/{id}/state`.** The transition was guarded only in Python: `change_state` did SELECT → `assert_transition` → UPDATE, a check-then-act with a TOCTOU window. R2 claimed "single UPDATE in one transaction; 409 on repeat", which was false. Two attorneys clicking "Mark reached out" together both got 200 | audit 01b check E21: 10 parallel PATCHes on one PENDING lead returned **2, 2 and 4 simultaneous 200s** across three rounds. My P0 report had claimed R2 was satisfied on the strength of a single clean 1/9 round — that round was luck, not a guarantee | **FIXED** — the guard moved into the SQL predicate: `UPDATE leads SET state=:new, updated_at=now WHERE id=:id AND state=:current`, `rowcount == 0` → `InvalidTransition` → 409. `assert_transition()` stays as an advisory pre-check for the error message. Live re-run: **5/5 rounds now give exactly one 200 and nine 409**. Regression barrier: `tests/test_state_concurrency.py` (5 parametrised rounds × 12 threads, plus a deterministic repository-level test). Verified the tests actually catch it by reverting the predicate — both fail against the old code |
| 7 | P0 | git `user.email` was a personal mailbox, which would be embedded in every commit object on a public repo | audit 01b check A4 | set to the GitHub noreply address; no commits existed yet, so nothing needed rewriting |
| 9 | P0 | `Content-Disposition` echoed the raw attacker-supplied filename: `urllib.parse.quote()` defaults to `safe="/"`, so a resume uploaded as `../../etc/passwd.pdf` produced `filename*=UTF-8''../../etc/passwd.pdf` — the storage key was sanitised but the header was not | audit 01b check D18 on the second pass; the first pass missed it because I only probed a quote and a non-ASCII name, both of which `quote()` does encode | **FIXED** — new `display_filename()` flattens to a basename and `quote(..., safe="")` encodes the rest. Kept separate from `sanitise_filename()` so Unicode survives: an accented resume name reaches the attorney intact rather than as `r_sum__se_or.pdf` |
| 13 | P1 | The honeypot path returned `None` against `response_model=LeadRead`, so every bot submission produced a **500** instead of the intended silent 202 | `test_honeypot_submission_is_silently_dropped` failed on first run | return a `Response` directly, which bypasses response-model validation |
| 17 | P2 | **Honeypot vs browser autofill — found by Bhavana in manual testing, not by the suite.** The hidden field was named `website`; Chrome's address autofill fills it for anyone with a saved profile (`autocomplete="off"` is advisory and Chrome ignores it), so genuine applicants were silently treated as bots. Worse, the API's 202 has an empty body and `requestJson` called `.json()` on it, throwing "Unexpected end of JSON input" — so the applicant saw a generic failure while their submission was discarded | manual browser testing by Bhavana. **Every automated layer passed**: the API test asserted 202, but nothing exercised the browser-plus-autofill path | renamed to `contact_ref_2` with `autocomplete="one-time-code"`, and `requestJson` now returns null for 202/204/empty bodies. Added an API assertion that the 202 body is empty and a Playwright step that fills the honeypot and still expects /thank-you |
| 18 | P2 | The test suite read the developer's `.env`. `test_state_concurrency.py` built its own `Settings()` without pinning the roster, so once `.env.example` shipped `ATTORNEYS` the tests logged in with the wrong password | **the real fresh clone in review 05 Part 2**: 6 tests failed there while all 154 passed in the working repo | added `build_settings(_env_file=None, ...)` so no test inherits ambient configuration; verified by re-running with `ATTORNEYS` forced into the environment |
| 16 | P2 | Updated `add_event`'s signature to carry the assignment columns but not its body — ruff had reformatted the `LeadEvent(...)` call onto one line between my two edits, so the string replace matched nothing and failed **silently**. Assignments worked; the audit trail recorded `to_assignee: None` | `test_assignment_writes_an_audit_row` failed. Same root cause as an earlier silent no-op edit on `change_state` | re-applied with an `assert old in s` guard. Every scripted edit now asserts its match rather than trusting it — a no-op replace is indistinguishable from success without one |
| 15 | P2 | Moved the per-state action table (`NEXT_ACTION`) into the `"use client"` button component and imported it from the server-rendered queue. A server component importing a value from a client module gets a **client-reference proxy, not the object**, so `NEXT_ACTION[state]` was silently `undefined` and every action cell rendered `—`. `tsc`, eslint and `pnpm build` all passed | the Playwright smoke test failed on `Mark reached out` not existing; confirmed by grepping the served HTML (`Mark reached out: 0`, `em-dash: 4`) | moved the table to a plain module `web/lib/lead-actions.ts`. **This is the strongest argument in the repo for the browser test**: three static gates were green while the primary action was missing from the page |
| 14 | P1 | Alembic autogenerated `add_column('tracking_code', nullable=False)`, which fails on any database that already holds leads — i.e. anyone who ran P0 | caught reading the generated migration before trusting it, then reproduced by seeding a 0001 database with 3 rows and upgrading | rewrote as add-nullable → backfill a unique code per row → set NOT NULL + UNIQUE; verified against a populated database (M3) |
| 11 | P0 | `/leads?offset=20` with only 4 leads rendered **"Showing 21–20 of 4"** over an empty table with headers and no empty state — the empty branch keyed off `total === 0` rather than "no rows on this page" | manual E2E pagination probe against the production build | empty state now keys off `items.length === 0`, with a distinct "Nothing on this page" message and a link back to the first page |
| 12 | P0 | in `pnpm dev` the session JWT appears verbatim in the `/leads` HTML inside the RSC flight payload (`["alma_token",{"value":"eyJ..."}]`) | manual E2E check 7, grepping the served HTML for a JWT | **dev-mode only** — the production build has zero occurrences (verified). No code change; recorded so the S1 claim is stated accurately as holding for production builds |
| 10 | P0 | first fix for #9 reused the ASCII-only storage sanitiser for the display name, mangling `résumé señor.pdf` → `r_sum__se_or.pdf` | caught by inspecting the live header immediately after the fix — no test would have failed | split into two functions; added `test_unicode_filename_survives_the_download_header` |
| 8 | P0 | staged 16 `.md` files with `git add -A`, violating the Markdown gate added to CLAUDE.md | audit 01b, re-reading CLAUDE.md before starting | `git rm --cached` on all 16; index now holds code only, files untouched on disk |

## Owner / architect interventions (Bhavana, via the planning session) — what changed because a human asked

| # | when | intervention | consequence |
|---|---|---|---|
| I1 | pre-build | Fixed roles: planning session = architect / PO / QA lead, never codes; Claude Code = implementer + tester. Written into CLAUDE.md and every prompt | agent stopped resolving architecture questions itself; 5 architect questions surfaced at P0 instead of silent decisions |
| I2 | pre-build | Required P0/P1/P2 scope review and explicit approval before any build | Playwright smoke added to P2; MinIO kept in P1 so the default quickstart stays Docker-free |
| I3 | pre-build | Privacy audit: no personal information in the repo beyond the first name; grep gate before every commit | caught wrong-person attribution in planning docs; a leaked home-directory path removed; later caught a personal mailbox in git identity (mistake #7) |
| I4 | P0 | Refused automatic per-stage commits — commits only after her review, agent stages and proposes messages | zero commits made until the P0 audit passed; nothing to rewrite |
| I5 | P0 | Demanded a proof-based pre-commit audit (32 checks, command + output, no assertions) — "prove it" | found the PATCH /state lost-update race (mistake #6) that the agent's own report had marked satisfied; 2 HIGH npm advisories; README depended on an unlisted tool |
| I6 | P0 | Markdown gate: no .md committed unless named by path under "MD FILES AUTHORIZED" | 16 staged docs unstaged (mistake #8); conversation-adjacent docs (PLAN §7) stay under her control until she decides what is submitted |
| I8 | P0 | Asked for public-facing threat review (DoS, malicious resume, prompt/agent injection) and product extensions (tracker code + status portal, status emails, attorney assignment, load dashboard) — planned and tiered before anything was told to the agent | docs/SECURITY_AND_EXTENSIONS.md; P1 gains 7 hardening items, P2 gains the status portal + notify hook + QUALIFIED; assignment + dashboard designed in DESIGN.md |
| I9 | P0 | History rewrite authorized once, pre-push, to add the newly-required `Review:` trailer and shorten the three commit messages. Granted only because nothing had been pushed (`origin/main` did not exist), and explicitly overriding CLAUDE.md's "never amend or rewrite history" | the agent had already committed under the superseded instructions and refused to rewrite unilaterally, surfacing it as a blocking question instead. Rebuilt each commit from its existing tree object rather than the working tree, so all three trees are byte-identical to the originals (`git diff pre-rewrite-backup HEAD` is empty) and only the messages changed; `pre-rewrite-backup` tag left in place as a safety net |
| I10 | P1 | Asked how optional intake fields (phone, address, reason, urgency) would be added without breaking required fields; chose typed-columns-plus-JSON-escape-hatch over all-JSON; roadmap only, no build | EXT6 in SECURITY_AND_EXTENSIONS.md; DESIGN.md brief in prompt 04 |
| I11 | P1 | Asked for a product + ops observability layer (usage, trends, backlog, bottlenecks; latency, security flags, access audit, upload metrics); reviewed three tiering options and chose design-only to protect the P2 feature box and the docs hour | OBS1–OBS9 in SECURITY_AND_EXTENSIONS.md §B2; DESIGN.md §8 brief in prompt 04b |
| I12 | P1 | Asked for clone-to-running bootstrap (requirements.txt, install script, setup instructions); planned as scripts/setup.sh + make setup/doctor/seed + generated requirements.txt fallback (uv.lock stays the source of truth) | Build C in prompt 04 |
| I13 | P1 | Challenged "Immigration lead intake" copy: the word came from the planning session's company research, not the assignment. Ruled: product copy stays at spec vocabulary; domain inference confined to DESIGN.md as a labelled assumption | REQUIREMENTS.md relabelled; prompt 05 check K; prompt 04b sentence |
| I14 | P2 | Asked for a usable, informative landing/intake design (contact-us shape, brief-matching look) with strictly zero functional change and a justification per change | docs/UI_CONCEPTS.md concept; prompt 04c, 35-min box, presentational files only |
| I15 | P2 | Decided to build the simplest attorney roster + assignment slice (three logins, assign-to-me, Mine tab, audited hand-offs) and paid for it by compressing the design pass, design doc and re-audit | prompt 04d; cuts recorded in prompts 04c/04b/05 |
| I16 | P2 | Ruled that make seed must never send email even with a Resend key present; split chore/style commits; committed screenshots | seed noop adapter + test; two commits |
| I17 | P2 | Gap review against production expectations and Alma's public job description: ruled the AI-native axis is the agent-driven build process, not an LLM in the product; transcripts are the critical missing submission item (hers); web unit tests added as a conditional fix; everything else stays roadmap | prompt 05 Part 1b; 04b sentence; sessions excerpts |
| I18 | P2 | Caught evaluation-oriented wording in repo docs and had it neutralised; added a vocabulary check to the release review | REQUIREMENTS/PLAN/UI_CONCEPTS/prompts/README reworded; check K |
| I19 | P2 | Found in manual testing that Chrome autofill fills the honeypot field and the client crashes on the resulting empty 202 body; ruled it a blocker for the release review with a two-part fix (client empty-body handling + autofill-proof honeypot) | prompt 05 check L |
| I20 | P2 | Tested real delivery via Resend; asked why the prospect email does not identify the attorney — ruled a content gap: status-change email names the assigned attorney with Reply-To, confirmation states an attorney will reach out; README documents the free-tier recipient limit | prompt 05 check M |
| I21 | P2 | Non-negotiable requirement: every submission is assigned to an attorney from the roster and the prospect confirmation CCs that attorney only; chose least-loaded assignment in the insert transaction, CC/Reply-To on the prospect email, shared inbox as empty-roster fallback | prompt 05 check N |
| I22 | P2 | Pre-push audit found console-mode email bodies print only at DEBUG while the default .env sets DEBUG=false — a fresh clone would never show email content or tracking codes; ruled the console adapter logs bodies at INFO (local-only by construction); Resend path stays redacted | final prompt fold-in |
| I23 | P2 | Asked about env/secret handling; confirmed .env never committed (.env.example is the template) and added SEC10: production secrets from a per-environment secrets manager, rotation, audit — roadmap | SECURITY_AND_EXTENSIONS SEC10; DESIGN.md roadmap row via final prompt |
| I7 | P0 | Overruled the agent's "P1" classification of the race: fix now, because committing with R2 asserted true would be false traceability | SQL-predicate guard + concurrency test folded into the P0 commit |

## Prompt → commit index

| Prompt | Stage | Commit(s) |
|---|---|---|
| `00-scaffold.md` | S0 | `chore(api): scaffold fastapi service`, `chore(web): scaffold next.js app and root tooling` |
| `01-p0-backend.md` | P0 | `feat(api): lead intake api with auth, state machine and email` |
| `01b-p0-audit.md` | P0 | (audit only — produced the race fix folded into the P0 commit) |
| `02-p0-frontend.md` | P0 | `feat(web): public apply form, attorney login, guarded leads table` |
| `03-p1-hardening.md` | P1 | `feat(api): s3 storage adapter and minio profile`, `feat(api): resend email adapter and html templates`, `chore: postgres profile, public-surface hardening, observability, ci` |
| `04-p2-docs.md` (Build A/B/C) | P2 | `feat: public status portal with tracking code`, `test(web): playwright e2e smoke`, `feat: prospect notifications on state change and QUALIFIED state`, `chore: reviewer bootstrap (...)` |
| `04c-p2-ui-polish.md` | P2 | `style(web): light theme, landing and intake copy, status/confirmation layout` |
| `04d-p2-assignment.md` | P2 | `feat: attorney roster and lead assignment` |
| `04e-p2-web-tests.md` | P2 | proposed: `test(web): unit tests and extended e2e coverage` |
| `04b-p2-design-doc.md` | P2 | docs only, not committed under the markdown gate |
| `05-p2-review.md` | P2 | proposed: `fix: ...`, `feat: auto-assign leads on submit and cc the assigned attorney` |

## Carried into P1 (agreed with the architect, for prompt 03)

- `send_intake_emails` must receive a plain snapshot, not the live ORM instance (it currently
  works only because `expire_on_commit=False`).
- Split the 409 vocabulary: add `already_in_state` (still HTTP 409) distinct from
  `invalid_transition`; the web client maps **only** `already_in_state` to the calm
  already-in-state notice. Today every 409 on that route is treated as benign, which is correct
  for a single legal edge and becomes wrong the moment a third state exists.
- Console email adapter: INFO logs recipient + subject + lead id only; full body drops to DEBUG.
- Placeholder credentials must hard-fail startup outside `local` (today they only warn).
- P2: document the dev-only token-in-flight-payload in DESIGN.md's security section, with the
  production-build verification that shows zero occurrences.
- P2: document the JWT `sub`-is-an-email decision (kept for P0; a stable user id when RBAC lands).

## Hand edits by Bhavana

| commit | what | why |
|---|---|---|
| | | |
