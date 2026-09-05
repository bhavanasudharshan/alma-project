# Requirements & traceability (FR / NFR → mechanism → stage → evidence)

Maintained by the planning session across iterations. Every row must point at a concrete artifact by P2.
**Invocation test**: if a user can invoke it, it is functional; if it constrains how every feature behaves, it is non-functional.

## Functional requirements

| ID | Requirement | Mechanism | Stage | Evidence (file / test) |
|---|---|---|---|---|
| FR1 | Prospect submits lead with first name, last name, email, resume — all required | `POST /api/v1/leads` multipart; pydantic + upload validation | P0 | `api/tests/test_leads_create.py` |
| FR2 | Prospect receives confirmation email | `EmailService.send` scheduled post-commit | P0 console → P1 Resend | `test_emails_sent_to_prospect_and_attorney` |
| FR3 | Attorney receives notification email with lead details | same, `ATTORNEY_NOTIFY_EMAIL` | P0 → P1 | same |
| FR4 | Attorney logs in | `POST /api/v1/auth/login` → JWT; cookie via Next route handler | P0 | `test_auth.py` |
| FR5 | Attorney lists leads with all submitted info | `GET /api/v1/leads` paginated, filter by state; `/leads` table | P0 | `test_leads_list.py`, manual E2E |
| FR6 | Attorney views/downloads resume | `GET /api/v1/leads/{id}/resume` (auth, streamed) | P0 | `test_resume_download.py` |
| FR7 | Lead starts `PENDING` | model default | P0 | `test_create_defaults_pending` |
| FR8 | Attorney manually marks `REACHED_OUT` | `PATCH /api/v1/leads/{id}/state`; transition table | P0 | `test_state_transitions.py` |
| FR9 | Illegal state transitions rejected | `InvalidTransition` → 409; `AlreadyInState` → 409 with a distinct code | P0/P1 | same |
| FR10 | Leads are auto-assigned to the least-loaded attorney on submit; attorneys can also claim unassigned leads and see all assignments | roster from `ATTORNEYS` config; `PATCH /api/v1/leads/{id}/assign`; `assigned_to` column set in the insert transaction + `lead_events` row; least-open-leads pick with roster-order tie-break; assignee is CC'd and Reply-To on the prospect confirmation and receives the notification; "Mine"/"Unassigned" tabs | P2 | `api/tests/test_assignment.py` (18), `api/tests/test_auto_assignment.py` (10), `web/e2e/smoke.spec.ts` |

## Non-functional requirements — CORE (must ship) vs ADVANCED (named, deferred, documented)

| ID | NFR | Tier | Mechanism | Stage | Why it matters |
|---|---|---|---|---|---|
| **Security** | | | | | |
| S1 | Internal data unreachable without auth | ★ core | JWT dependency on every internal route; `middleware.ts` on `/leads*`; token only in httpOnly cookie, never in client JS | P0 | token never crosses to the browser runtime; resume download proxied server-side |
| S2 | Untrusted uploads are bounded | ★ core | extension + content-type allow-list, size cap, sanitised storage key, path-traversal-safe local adapter, object storage isolates bytes from the app host | P0/P1 | says out loud: content sniffing / AV scan is the next layer |
| S3 | Secrets never in repo; config explicit | ★ core | pydantic-settings, `.env.example`, `.gitignore`, review grep in prompt 05 | S0 | one config surface, every setting documented |
| S4 | Credentials never stored plain | ★ core | bcrypt hash at startup; constant-time verify | P0 | |
| S5 | Browser cross-origin locked | ★ core | CORS allow-list from settings; `sameSite=lax` cookie | P0/P1 | |
| S6 | Abuse of public endpoint | advanced | rate limit / CAPTCHA on `POST /leads` | stretch / DESIGN.md | named + deferred with the mechanism |
| S7 | Authorization beyond one role | advanced | RBAC (attorney vs admin), per-lead audit log | DESIGN.md | |
| **Reliability / correctness** | | | | | |
| R1 | A submitted lead is never lost because email failed | ★ core | persist + commit first; emails in `BackgroundTasks`; provider errors logged, not raised | P0 | explicit ordering decision with its price (at-most-once email) |
| R2 | State changes are atomic and idempotent-safe | ★ core | guard is the SQL predicate `UPDATE leads SET state=:new WHERE id=:id AND state=:current`; `rowcount == 0` → 409. `assert_transition()` is an advisory pre-check for the message only | P0 | `test_state_concurrency.py::test_exactly_one_concurrent_patch_wins` (5 runs × 12 parallel), `::test_sql_predicate_rejects_a_stale_expected_state` (deterministic) |
| R3 | Guaranteed email delivery | advanced | transactional outbox + worker + retries | DESIGN.md | v2 diagram delta |
| R4 | Duplicate submissions | advanced | idempotency key / email+time dedupe | DESIGN.md | |
| **Maintainability** | | | | | |
| M1 | Clear layering, no logic in transport | ★ core | routers → services → repositories → db; services FastAPI-free | S0/P0 | testable without HTTP |
| M2 | Behaviour under test | ★ core | pytest with fakes for storage/email; web lint + typecheck; CI on push | P0/P1 | fakes over mocks; CI blocks red |
| M3 | Schema evolution | ★ core | Alembic migrations from the first table | P0 | |
| M4 | Config vs deploy | ★ core | adapter selection by env, no code change to switch DB/storage/email | P1 | selection matrix in README |
| M5 | Observability | ★ core | request-id middleware, structured logs, health with DB check | P1 | one line to trace a request end to end |
| M6 | Consistent errors | ★ core | global handlers → `{detail, code}` envelope | P0/P1 | |
| **Extensibility** | | | | | |
| E1 | New lead states | ★ core | single transition table; enum; 409 handler | P0 | adding `CLOSED` = one dict entry + one enum value |
| E2 | New providers (email/storage/db) | ★ core | Protocol adapters; DB via connection string | P0/P1 | swap without touching services |
| E5 | Roster → attorneys table | ★ core | attorneys live in `ATTORNEYS` config today; `Settings.roster` is the single read point, and `AttorneyDirectory` the single consumer, so an `attorneys` table replaces both without touching routers or services. `leads.assigned_to` holds an email, which becomes an FK in the same migration | P2 → DESIGN.md | the upgrade is one adapter and one migration, not a rewrite |
| E3 | New lead fields | ★ core | pydantic schema + model + migration; web types mirror | P0 | documented recipe in DESIGN.md |
| E4 | Typed API client | advanced | OpenAPI → TS types (`openapi-typescript`) | stretch | |
| **Scalability / performance** | | | | | |
| P1 | Request path stays fast | ★ core | email off the request path; file streamed, not buffered; pagination + indexes on `state`,`created_at` | P0 | |
| P2 | Stateless API | ★ core | no session state; JWT; files in object storage (P1). Exception: rate-limit counters are per-process with the default `memory://` store — `RATE_LIMIT_STORAGE_URL` switches to Redis at deploy | P1 | horizontal scale is a replica count once the limiter store is shared |
| P3 | Scale ladder | advanced | 1x: single Postgres + object storage holds · 10x: email worker + read replica · 100x: queue-backed ingestion, CDN for uploads, search index for leads | DESIGN.md | name what breaks first, not what you'd add |
| **Availability** | | | | | |
| A1 | Degrade gracefully when provider down | ★ core | email failure isolated; storage failure → 503 with clear code, lead not created | P0/P1 | |
| A2 | HA deploy | advanced | multi-replica API, managed Postgres, object storage SLA | DESIGN.md | |
| **Compliance / privacy** | | | | | |
| C1 | PII handling stated | ★ core | resumes in private bucket, never public URLs; retention policy named | P1/DESIGN.md | |
| C2 | Retention / deletion | advanced | TTL + delete endpoint | DESIGN.md | |
| **Cost** | | | | | |
| $1 | Zero-infra local run | ★ core | SQLite + local disk + console email default | S0/P0 | anyone can run it in minutes without accounts |

## Domain context — ASSUMPTION, not in the assignment (DESIGN.md only, never in product copy)
- The assignment names only "an attorney inside the company". Alma's own public job description states its first market is immigration law; this inference shapes ONLY the PII posture below and is stated in DESIGN.md as an assumption. UI, API and email vocabulary stay at the spec's level: lead, prospect, attorney, résumé. If the inference is right: a lead is a prospective visa client; the resume is what an attorney uses to assess eligibility (e.g. O-1/H-1B). Treat resumes as sensitive PII of people in an immigration process → private storage, no public URLs, named retention policy (C1/C2).
- `PENDING → REACHED_OUT` is the first step of an intake pipeline; the transition table is designed to grow (e.g. QUALIFIED, ENGAGED, DECLINED) without touching routers (E1).

## Verification checklist (release review)

- Every ★ core row has code + a test or a lint/CI gate; every advanced row is named in `docs/DESIGN.md` with mechanism + price, not hand-waved.
- `DESIGN.md` decision table uses the fixed grammar `Area | Driver | Choice | Rejected alternative | Price paid`.
- One volunteered limitation stated unprompted (at-most-once email).
- Scale section names what breaks first at 10x and the shape change at 100x.
- The agent-usage writeup states what was delegated, what was kept, and one real caught mistake.
