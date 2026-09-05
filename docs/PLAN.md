# Alma Lead Intake — Delivery Plan

> Working model: this plan + tracking live in the Cowork/Claude planning session (Bhavana + Claude).
> Claude Code executes one prompt per stage from `docs/agent/prompts/`. Every stage ends in a git commit.
> Hard constraint: GitHub link uploaded within **6 hours** of starting.

## 1. Requirements → deliverables map

| # | Requirement (from assignment) | Where it lands | Stage |
|---|---|---|---|
| F1 | Public form: first name, last name, email, resume/CV | `web/app/(public)/apply`, `POST /api/v1/leads` (multipart) | P0 |
| F2 | On submit, email prospect **and** attorney | `api/app/services/email/` (Resend adapter + console fallback) | P0 (console) → P1 (Resend) |
| F3 | Internal UI, auth-guarded, lists all lead info | `web/app/(internal)/leads`, `GET /api/v1/leads` | P0 |
| F4 | State `PENDING` → `REACHED_OUT`, manual by attorney | `PATCH /api/v1/leads/{id}/state`, state-machine guard | P0 |
| T1 | System design | `docs/REQUIREMENTS.md` (FR/NFR traceability, S0) + `docs/DESIGN.md` (finished P2) | S0 / P2 |
| T2 | FastAPI APIs, Next.js web | `api/`, `web/` | S0 |
| T3 | Storage + email service | SQLite (default) / Postgres (compose); MinIO/S3 for resumes; Resend | P0 / P1 |
| T4 | Production-level structure | layered api (routers→services→repos), typed web, lint, tests, CI | S0 → P1 |
| S1 | Public GitHub repo | `git remote add origin …`, push at P2 | P2 |
| S2 | How-to-run doc | `README.md` | S0 skeleton → P2 |
| S3 | Design doc (why/how) | `docs/DESIGN.md` | P2 |
| S4a | Agent-usage writeup (½ page) | `docs/AGENT_USAGE.md` (living draft from S0, trimmed at P2) | S0→P2 |
| S4b | Prompt logs / transcripts | `docs/agent/prompts/*.md`, `docs/agent/sessions/*.md` | continuous |
| S4c | Attribution | `NOTES.md` + commit trailers (`Agent: claude-code` / `Author-mode: hand-written`) | continuous |
| S5 | Screen recording | Loom, link in README | P2 |

## 2. Architecture (decided)

```
 Prospect ──► Next.js /apply ──multipart──► FastAPI POST /leads ──► LeadService
                                                                     ├─ LeadRepository (SQLAlchemy → SQLite | Postgres)
                                                                     ├─ FileStorage    (LocalDisk [P0] → S3/MinIO [P1])
                                                                     └─ EmailService   (Console [P0] → Resend [P1])  ──► prospect + attorney
 Attorney ──► Next.js /login ──► POST /auth/login ──JWT──► httpOnly cookie (Next route handler)
          ──► Next.js /leads ──► GET /leads, PATCH /leads/{id}/state  (Bearer via server-side fetch)
```

Decisions and their price (full reasoning goes into `docs/DESIGN.md`):

| Area | Choice | Why | Price paid |
|---|---|---|---|
| DB | SQLAlchemy 2.x + Alembic; SQLite default, Postgres via `docker compose --profile pg` | one-command local run; real migrations | two engines to smoke-test |
| Files | `FileStorage` protocol; `LocalDiskStorage` in P0, `S3Storage` (boto3, MinIO endpoint) in P1 | P0 stays Docker-free; production story is real S3 | pre-signed download URLs add a code path |
| Email | `EmailService` protocol; `ConsoleEmailService` when `RESEND_API_KEY` unset, `ResendEmailService` otherwise | runs without secrets; provider swap is one class | no delivery guarantees in demo mode |
| Email timing | FastAPI `BackgroundTasks` after commit | request returns fast; failure never loses the lead | at-most-once; note outbox pattern as the upgrade |
| Auth | Backend-issued JWT (HS256, `python-jose`/`pyjwt`), seeded attorney from env; Next.js route handler sets httpOnly cookie, server components forward Bearer | single auth authority; no NextAuth surface to explain | no refresh tokens (8h expiry, documented) |
| State | Enum + explicit transition table `{PENDING: {REACHED_OUT}}`; 409 on illegal transition | trivially extensible (e.g. `CLOSED`) | none |
| Web | Next.js 15 App Router, TypeScript, Tailwind, `zod` + `react-hook-form`, server actions/route handlers talk to API | idiomatic, typed end to end | no shared type package (OpenAPI types generated in P1 if time) |
| Repo | monorepo: `api/` (uv), `web/` (pnpm), `docker-compose.yml`, `Makefile` | single clone, single `make dev` | none |

Out of scope (state in DESIGN.md): rate limiting/CAPTCHA on the public form, virus scanning of uploads, multi-tenant attorneys, email retries/outbox, i18n.

## 3. Repo layout (target)

```
alma/
├── README.md                 # how to run (S2)
├── NOTES.md                  # attribution: agent-generated vs hand-written (S4c)
├── CLAUDE.md                 # conventions Claude Code must follow
├── Makefile                  # make dev | api | web | test | lint | seed
├── docker-compose.yml        # profiles: pg (postgres), s3 (minio)
├── .env.example
├── api/                      # FastAPI, managed by uv
│   ├── pyproject.toml
│   ├── alembic/ + alembic.ini
│   ├── app/
│   │   ├── main.py           # app factory, CORS, routers, lifespan
│   │   ├── core/             # config (pydantic-settings), security (jwt), deps, logging
│   │   ├── db/               # session, base, models/
│   │   ├── schemas/          # pydantic I/O models
│   │   ├── repositories/     # LeadRepository
│   │   ├── services/         # lead_service, email/{base,console,resend}, storage/{base,local,s3}
│   │   └── api/v1/           # routers: health, auth, leads
│   └── tests/                # pytest + httpx AsyncClient; fakes for email/storage
├── web/                      # Next.js 15 App Router, pnpm
│   ├── app/(public)/apply, app/(public)/thank-you
│   ├── app/(internal)/login, app/(internal)/leads
│   ├── app/api/auth/{login,logout}/route.ts   # cookie set/clear
│   ├── lib/api.ts (typed fetch), lib/auth.ts (cookie helpers), middleware.ts (guard /leads)
│   └── components/
└── docs/
    ├── PLAN.md               # this file
    ├── DESIGN.md             # S3
    ├── AGENT_USAGE.md        # S4a
    └── agent/prompts/*.md, agent/sessions/*.md   # S4b
```

## 4. Stages, acceptance criteria, commits

Time budget assumes a 6h clock. Planning (this doc) is ~30 min before the clock or inside it — decide before starting.

### Stage 0 — Scaffold (target 30 min) → commit `chore: scaffold monorepo (api/web/docs)`
Prompt: `00-scaffold.md`
- `api/`: uv project, FastAPI app factory, `/api/v1/health`, pydantic-settings config, ruff + pytest configured, one passing test.
- `web/`: `create-next-app` (TS, Tailwind, App Router, ESLint), typed API client stub pointing at `NEXT_PUBLIC_API_URL`.
- Root: `Makefile`, `.env.example`, `.gitignore`, `README.md` skeleton, `NOTES.md`, `CLAUDE.md`, `docs/DESIGN.md` skeleton (headings only).
- **Accept**: `make api` serves health; `make web` renders; `make test` green; `make lint` clean.

### P0 — Vertical slice, E2E working, zero external deps (target 2h) → 2 commits
Prompt `01-p0-backend.md` → commit `feat(api): leads CRUD, state machine, console email, local file storage, jwt auth`
- Models: `Lead(id uuid, first_name, last_name, email, resume_key, resume_filename, resume_content_type, state, created_at, updated_at)`; Alembic initial migration.
- `POST /api/v1/leads` multipart (validates fields, MIME/size of resume ≤ 5MB, pdf/doc/docx), stores file via `FileStorage`, persists, schedules two emails via `BackgroundTasks`. Returns 201.
- `POST /api/v1/auth/login` → JWT for seeded attorney (`ATTORNEY_EMAIL`/`ATTORNEY_PASSWORD` env, bcrypt-hashed at startup).
- `GET /api/v1/leads` (auth, paginated, filter by state), `GET /api/v1/leads/{id}` (auth), `GET /api/v1/leads/{id}/resume` (auth, streams file), `PATCH /api/v1/leads/{id}/state` (auth, transition table, 409 on invalid).
- Tests: create lead (happy + validation), auth required on internal routes, state transition valid/invalid, emails captured by `FakeEmailService`.
- **Accept**: curl walkthrough in README works; pytest green.

Prompt `02-p0-frontend.md` → commit `feat(web): public apply form, login, guarded leads table with mark-reached-out`
- `/apply`: form with zod validation, file input, success → `/thank-you`; server-side error display.
- `/login`: posts to Next route handler → calls API → sets httpOnly cookie; `middleware.ts` redirects unauthenticated `/leads` to `/login`.
- `/leads`: server component fetches with Bearer from cookie; table with all fields, state badge, resume link, "Mark reached out" button (server action → PATCH → revalidate). Filter tabs PENDING / REACHED_OUT / ALL.
- **Accept**: full manual E2E on localhost; no console errors; `pnpm lint` + `tsc --noEmit` clean.

### P1 — Production hardening (target 1.5h) → commit `feat: s3 storage, resend email, postgres profile, ci`
Prompt `03-p1-hardening.md`
- `S3Storage` (boto3) selected when `S3_ENDPOINT_URL` set; MinIO in `docker-compose --profile s3`, bucket bootstrap on startup; pre-signed GET for resume download (or proxy stream — pick one, document).
- `ResendEmailService` selected when `RESEND_API_KEY` set; HTML+text templates in `services/email/templates/`; attorney recipient from `ATTORNEY_NOTIFY_EMAIL`.
- Postgres via `docker compose --profile pg`; `DATABASE_URL` switch; Alembic verified on both.
- Cross-cutting: request-id middleware + structured logging, consistent error envelope, CORS locked to web origin, OpenAPI tags/examples, `GET /health` checks DB.
- GitHub Actions: ruff + pytest + `pnpm lint` + `tsc`.
- Tests extended: storage fake, S3 adapter unit test with `moto` (if time), email template rendering.
- **Public-surface hardening (approved, see docs/SECURITY_AND_EXTENSIONS.md)**: SEC1 per-IP rate limiting on `POST /leads` + `POST /auth/login` (slowapi, 429 + Retry-After); SEC2 magic-byte sniffing, accept `.pdf`/`.docx` only, resumes served as attachment + `nosniff`; SEC3 Jinja2 autoescape in email templates, CR/LF stripped from subjects, DESIGN.md "no LLM in the loop / injection rule" section; SEC4 honeypot field; SEC6 security headers on API and web; SEC9-lite `lead_events` table written on every state change; EXT1 `tracking_code` column (≥128-bit base32) generated at create and included in the prospect email; EXT2 `notify_prospect` flag on the transition table (no sends yet).
- **Accept**: `docker compose --profile pg --profile s3 up` + `make dev` passes the same E2E; CI green on push.

### P2 — Polish + submission (target 1h, hard stop at 5h30) → commits `docs: …`, final push
Prompts `04-p2-docs.md`, `05-p2-review.md`
- `README.md` complete: prerequisites, 3-command quickstart (SQLite/console mode), full-stack mode (compose), env table, curl examples, test/lint commands, Loom link.
- `docs/DESIGN.md`: requirements, architecture diagram, decision table with prices, data model, API contract, state machine, security notes, what I'd do next.
- `docs/AGENT_USAGE.md` (½ page): tools, delegated vs hand-written, **the one bug the agent introduced and how it was caught** (log candidates in `NOTES.md` as they occur — do not invent at the end).
- `docs/agent/sessions/`: paste 3–4 transcript excerpts (scaffold, the bug, a refactor request).
- `NOTES.md` finalized; verify commit trailers.
- **Approved P2 features (time-boxed 60 min total, BEFORE docs; if overrun, ship the portal and move the rest to EXT)**: EXT1 public status portal — `GET /api/v1/leads/track/{code}` (rate-limited, returns state + timestamps only) and `/status` page; EXT2 hook — prospect email on `REACHED_OUT` via the `notify_prospect` flag; EXT5 — add `QUALIFIED` state (REACHED_OUT → QUALIFIED) with badge and button, as the extensibility demo.
- Playwright E2E smoke (`web/e2e/smoke.spec.ts`: apply → login → mark reached out → badge flips), run in CI. Time-boxed to 25 min; if P1 overran, defer and record the deferral in NOTES.md.
- Self-review prompt `05`: agent audits its own repo against this checklist and reports gaps; Bhavana decides fixes.
- Push to public GitHub; record 3–5 min Loom: apply → email in console/Resend → login → list → mark reached out → refresh → filter.

### Stretch (only if ≥45 min remain before hard stop, AFTER the Loom is recorded and the link submitted)
- Hosted demo on Railway: API + web services, Railway Postgres, S3/local-disk storage, console email (no sending domain), free `*.up.railway.app` subdomain; add to README as "Live demo (email disabled)". Never at the expense of P2 docs.
OpenAPI → TS types (`openapi-typescript`); rate-limit on `POST /leads`; `CLOSED` state to demonstrate extensibility.

## 4b. Stage approval
P0, P1, P2 scope reviewed and approved by Bhavana before build start (planning session). Change of scope after approval = an explicit note in this file + NOTES.md.

## 4c. Independent verification by Bhavana (before push)
On this machine in a different folder, or on a second computer with uv + node + pnpm installed:
```
git clone git@github.com:<owner>/alma-project.git ~/tmp/alma-verify && cd ~/tmp/alma-verify
make setup        # prints URLs and where credentials live
make verify-clone # setup + doctor + tests + health probes, timed
make dev          # then browser: /apply → /login → /leads → /status
```
Target: under 5 minutes wall-clock from clone to first page, zero manual steps. Anything else is a README bug fixed before push.

## 4d. Endgame parallel plan (P2 close-out)
Agent: 04d commit → subagents A (04e web tests: web/**, Makefile, ci.yml) ‖ B (04b design doc + product guide: docs/DESIGN.md, docs/PRODUCT_GUIDE.md, prompts/README.md) → parent reconciles NOTES.md, full gates → 05 re-audit + release checklist (sequential; fixes staged as `fix:`).
Bhavana, in parallel from now: transcript excerpts → docs/agent/sessions/; MD FILES AUTHORIZED list; Loom script; second-machine clone access. After 05: authorize test(web) + fix + docs commits → push → public → make verify-clone elsewhere → Loom → submit.

## 5. Working protocol per stage

1. Cowork session: confirm stage prompt, mark task in_progress.
2. Bhavana runs `claude` in the repo root, pastes the prompt file contents (or `claude "$(cat docs/agent/prompts/NN-*.md)"`).
3. Claude Code implements, runs `make test lint`, and either commits (if authorized in the kickoff message) or stages the changes and proposes commit messages in its report. Default for S0–P0: no commits until Bhavana has reviewed and confirmed P0; the proposed messages are then used as-is.
4. Bhavana saves a transcript excerpt to `docs/agent/sessions/NN-<stage>.md` (`/export` in Claude Code or copy-paste).
5. Bhavana reports back to the planning session: what passed, what the agent got wrong. Cowork logs it in `NOTES.md` candidate list and adjusts the next prompt.
6. Every hand edit Bhavana makes gets its own commit with `Author-mode: hand-written`.

## 6. Time plan (6h clock)

| Clock | Stage |
|---|---|
| pre-clock | `docs: plan` commit by Bhavana (hand, after fixing git identity) |
| 0:00–0:30 | Stage 0 scaffold + commit |
| 0:30–2:30 | P0 backend, P0 frontend, 2 commits, manual E2E |
| 2:30–4:15 | P1 hardening (+45 min public-surface security, audit table, tracking code) + commit, CI green |
| 4:15–5:15 | P2 features (portal, notify hook, QUALIFIED; 60 min box) then docs, writeup, self-review |
| 5:15–5:45 | Push public, Loom recording, upload link |
| 5:45–6:00 | Buffer — hard stop |

## 7. Architect decisions log (answers to Claude Code questions)

| Stage | Question | Decision | Rationale |
|---|---|---|---|
| S0 | Pre-declare later-stage config? | Yes, full surface in P0 with safe defaults | one complete config table |
| S0 | Who commits planning docs? | Planning docs first, `Author-mode: agent-assisted` | accurate attribution |
| S0 | web/README.md | delete in P0 frontend | one run doc |
| P0 | Console email logs full PII | P1: INFO = recipient + subject + lead id; body at DEBUG; local `.env.example` defaults LOG_LEVEL=DEBUG so the demo still shows bodies | C1 without losing demo value |
| P0 | 409 on repeated PATCH from UI | Backend stays strict; web treats 409 on that route as "already in that state" → refresh, informational notice, not an error | R2 correctness server-side, calm UX client-side |
| P0 | Placeholder credentials outside local | P1: hard-fail startup when ENVIRONMENT != local and any placeholder secret is in use | S3 |
| P0 | JWT `sub` is an email | Keep for P0/P1; document in DESIGN.md that RBAC (S7) introduces a users table and `sub` becomes a stable id | no speculative complexity |
| P0 | Background email gets the ORM `Lead` after session close | P1: pass a plain snapshot (dataclass/pydantic) to `send_intake_emails`, not the ORM object | detached-instance risk if a lazy relationship is ever added |
| P0 audit | Lost-update race on PATCH /state (check 21: 2/2/4 concurrent 200s) | Fix NOW, not P1: guard moves into the SQL predicate (`UPDATE … WHERE id=:id AND state=:current`, rowcount 0 → InvalidTransition), concurrent test added | committing with R2 asserted true would be false traceability; it is also the writeup's headline caught-mistake |
| P0 audit | web/README.md deleted despite prompt 01 "don't touch web/" | Confirmed — architect answer supersedes prompt constraint | one run doc |
| P0 audit | Early docs commit to protect untracked .md? | No — Bhavana controls md commits; she keeps an out-of-repo backup meanwhile | markdown gate |
| P0 audit | alembic/versions/.gitkeep redundant | Remove now | trivial |
| P0 | Public-surface security & extensions proposal | SEC1/2a-d/3/4/6/9-lite + EXT1 column + EXT2 flag → P1; EXT1 portal + EXT2 hook + QUALIFIED → P2 (60-min box); ClamAV/Turnstile/EXT3/EXT4 → DESIGN.md | public form on the open internet; extensions show product thinking; box protects the docs hour |
| P1 | Docker absent on the build machine — Postgres/MinIO unverified | Postgres verified via a `postgres:16` service container in CI (alembic + pytest); MinIO covered by moto only, README says so plainly | proof on every push beats a one-off laptop check; never claim untested paths |
| P1 | `sample_test_data/` fixture folder untracked | gitignore it | may hold real résumés later |
| P1 | Web has no automated tests | Playwright stays P2, moved to run immediately after the status portal | P1 added three frontend behaviours only manually verified |
| P1 | `memory://` rate-limit store contradicts "stateless" | REQUIREMENTS P2 softened: stateless except per-process limiter counters; Redis via `RATE_LIMIT_STORAGE_URL` | truthfulness over slogan |
| P2 | Features finished in 19 of 85 min; Build C ordering; seed; e2e DB; silent missing copy | Build C now; seed 4 leads across 3 states; Playwright uses a throwaway SQLite via env; missing STATUS_COPY for a notify state fails a test | populated demo, no dev-db pollution, notifications must never silently no-op |
| P2 | Attorney roster + assignment requested late | Build the simplest slice (config roster, assigned_to, assign-to-me, Mine tab, events, seed, tests; 60-min box); compress 04c→20, 04b→20, 05→25, Loom one take | needed for the demo story; auth touched so the re-audit stays |
| P2 | Build C + UI pass review | Two commits split by path; make seed never sends email (noop adapter, tested); docs/img screenshots committed with style commit (example.com data only); verify-clone stays local | seed must not fire real emails; screenshots strengthen README |
| P2 | Assignment slice review | No FK on assigned_to (config roster); make doctor warns on orphaned assignees; .env.example ships the three-attorney roster uncommented; SecretStr on Attorney.password; assignment documented as built in DESIGN.md | historical fact outlives config; demo shows real names |
| P2 | Evaluation vocabulary in docs | Removed evaluation-oriented wording from all repo docs; check K extended | docs describe the system, never the evaluation |
| P2 | Auto-assign + CC attorney (owner: non-negotiable) | Least-loaded pick in the insert transaction, event row, prospect email CC + Reply-To assignee, notification to assignee, shared inbox only as empty-roster fallback | simplest version that makes assignment real at intake; free-tier CC caveat documented |
| P2 | Separate ROADMAP.md? | No — roadmap stays as DESIGN.md §11; H1 becomes "Design & Roadmap — Alma Lead Intake"; README link text says "design and roadmap"; filename unchanged (16 references) | one document, one vocabulary, no dangling links |
