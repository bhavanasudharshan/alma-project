# Alma Lead Intake

Public lead form + internal, auth-guarded lead queue for an immigration law firm.
FastAPI (`api/`) and Next.js 15 (`web/`) in one repo.

> **Status: P1.** Lead intake works end to end, with S3/MinIO and Resend adapters,
> a Postgres profile, rate limiting, upload content sniffing, an audit trail and CI.
> The default run still needs no Docker and no accounts.

## Quickstart

```bash
git clone <repository-url> && cd alma-project
make setup
make dev
```

That is the whole thing. `make setup` checks your tools, installs both dependency sets,
creates `.env` from `.env.example` if you do not have one, and runs the migrations. The
default configuration needs **no Docker and no accounts**: SQLite on disk, resumes on
the local filesystem, and emails printed to the API log instead of sent.

| | |
|---|---|
| Web app | http://localhost:3000 |
| Public form | http://localhost:3000/apply |
| Status portal | http://localhost:3000/status |
| Attorney sign-in | http://localhost:3000/login |
| API docs | http://localhost:8000/docs |
| Health | http://localhost:8000/api/v1/health |

The attorney credentials are `ATTORNEY_EMAIL` and `ATTORNEY_PASSWORD` in your `.env`.
They ship as local-only placeholders — the app refuses to start with them outside
`ENVIRONMENT=local`.

```bash
make seed     # four demo leads across PENDING / REACHED_OUT / QUALIFIED
make doctor   # if something is not working, run this first
```

### Prerequisites

`make setup` checks these and prints the right install command if one is missing.

| Tool | Minimum | macOS | Linux | Windows (WSL) |
|---|---|---|---|---|
| [uv](https://docs.astral.sh/uv/) | any recent | `brew install uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | same as Linux |
| Node | 20 (22 recommended) | `brew install node@22` | [NodeSource](https://github.com/nodesource/distributions) | same as Linux, inside WSL |
| pnpm | 9 | `corepack enable && corepack prepare pnpm@9 --activate` | same | same |
| Docker | optional | Docker Desktop | Docker Engine | Docker Desktop + WSL2 |

Python itself is not a prerequisite: uv installs and pins the 3.12 toolchain.
Docker is only needed for the Postgres and MinIO profiles.

### Prefer pip?

`api/requirements.txt` is exported from `uv.lock` (CI fails if the two drift), so a
plain virtualenv works too:

```bash
cd api && python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head && uvicorn app.main:app --reload
```

You still need Node and pnpm for the web app.

### Verifying it works on another machine

```bash
make verify-clone
```

Clones this repository into a temporary directory and runs setup, doctor, the test
suite and both servers, then checks that the API and the public pages answer. It prints
a wall-clock time and fails if anything needed a manual step.

## Full-stack mode

Every backing service is opt-in and selected by environment variables alone — no code
change switches the database, the file store or the email provider (M4/E2).

```bash
# Postgres instead of SQLite
docker compose --profile pg up -d
export DATABASE_URL=postgresql+psycopg://alma:alma@localhost:5432/alma
make migrate

# MinIO instead of local disk
docker compose --profile s3 up -d
export S3_ENDPOINT_URL=http://localhost:9000
export S3_ACCESS_KEY_ID=minioadmin S3_SECRET_ACCESS_KEY=minioadmin

make dev
```

> **Verification status.** Postgres is exercised in CI: a `postgres:16` service
> container runs the migrations and the full test suite on every push. The MinIO
> compose profile is provided, but the S3 adapter is verified via `moto` in CI, not
> against live MinIO in this submission.

### Adapter selection matrix

| Environment | Database | File storage | Email |
|---|---|---|---|
| *(nothing set — the default)* | SQLite | Local disk | Console (logged) |
| `S3_ENDPOINT_URL` or `S3_ACCESS_KEY_ID` set | — | S3 / MinIO | — |
| `RESEND_API_KEY` set | — | — | Resend |
| `DATABASE_URL=postgresql+psycopg://…` | Postgres | — | — |

Unset provider keys mean "that adapter is not selected", so anyone with no accounts
and no Docker gets a working system.

## Configuration

Every setting lives in `api/app/core/config.py` and is documented in `.env.example`.

| Variable | Default | Purpose |
|---|---|---|
| `APP_NAME` | `Alma Lead Intake API` | OpenAPI title |
| `ENVIRONMENT` | `local` | Deployment label |
| `DEBUG` | `false` | FastAPI debug mode |
| `API_V1_PREFIX` | `/api/v1` | Route prefix |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Browser origin allow-list |
| `DATABASE_URL` | `sqlite:///./data/alma.db` | SQLAlchemy URL |
| `JWT_SECRET_KEY` | `dev-only-change-me` | JWT signing key — replace before deploy |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | Token lifetime (8h, no refresh) |
| `ATTORNEY_EMAIL` / `ATTORNEY_PASSWORD` | `attorney@example.com` / `changeme` | Seeded login, bcrypt-hashed at startup |
| `UPLOAD_DIR` | `uploads` | Resume directory for local-disk storage |
| `MAX_RESUME_MB` | `5` | Upload size cap |
| `ATTORNEY_NOTIFY_EMAIL` | `attorney@example.com` | Inbox for new-lead notifications |
| `RESEND_API_KEY` | unset | Unset → console email; set → Resend |
| `ATTORNEYS` | three demo accounts | JSON roster; delete for the single-account fallback |
| `S3_ENDPOINT_URL` | unset | Unset → local disk; set → S3/MinIO |
| `RATE_LIMIT_LEADS` / `RATE_LIMIT_LOGIN` | `5/10minutes` / `10/5minutes` | Per-IP budgets |
| `RATE_LIMIT_STORAGE_URL` | `memory://` | Per-process counters; point at Redis to share limits across replicas |
| `LOG_JSON` | `false` | One JSON object per log line |
| `REQUEST_ID_HEADER` | `X-Request-ID` | Honoured inbound, echoed on every response |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | API base URL used by the web app |

## API

Interactive docs at `http://localhost:8000/docs` once the API is running.

| Method | Path | Auth | Success | Errors |
|---|---|---|---|---|
| `GET` | `/api/v1/health` | — | 200 | — |
| `POST` | `/api/v1/auth/login` | — | 200 | 401 bad credentials · 429 rate limited |
| `POST` | `/api/v1/leads` | — | 201 (202 if honeypot tripped) | 422 invalid fields · 415 bad/mismatched type · 413 too large · 429 rate limited · 503 storage down |
| `GET` | `/api/v1/leads` | Bearer | 200 | 401 · 422 bad paging |
| `GET` | `/api/v1/leads/{id}` | Bearer | 200 + audit trail | 401 · 404 |
| `GET` | `/api/v1/leads/{id}/resume` | Bearer | 200 stream | 401 · 404 |
| `PATCH` | `/api/v1/leads/{id}/state` | Bearer | 200 | 401 · 404 · 409 `already_in_state` or `invalid_transition` |
| `PATCH` | `/api/v1/leads/{id}/assign` | Bearer | 200 (idempotent) | 401 · 404 · 422 `unknown_assignee` |
| `GET` | `/api/v1/leads/track/{code}` | — | 200 state + timeline | 404 · 429 |

Every error uses the same envelope: `{"detail": "...", "code": "..."}`.

**Uploads** must be PDF or DOCX, 5 MB or less, and the declared content type, the file
extension and the actual leading bytes must all agree — renaming `evil.exe` to `cv.pdf`
is rejected with 415.

**Rate limits** are per IP: 5 submissions / 10 min, 10 logins / 5 min, 20 status
lookups / min. Exceeding one returns 429 with `Retry-After`.

### Attorneys and assignment

`ATTORNEYS` in `.env` is a JSON array of `{email, password, name}`. Three ship by
default; delete the line and the single `ATTORNEY_EMAIL`/`ATTORNEY_PASSWORD` account
becomes the only login.

Every submission is **auto-assigned to the attorney with the fewest open leads**
(`PENDING` or `REACHED_OUT`; ties go to roster order), in the same transaction as the
insert, so a lead is never briefly ownerless. That attorney is copied on the
prospect's confirmation and is the `Reply-To` on it, and receives the new-lead
notification directly. With no roster configured, leads stay unassigned and the
notification falls back to `ATTORNEY_NOTIFY_EMAIL`.

The queue has **Mine** and **Unassigned** tabs and an "Assign to me" button on
unassigned rows. Reassigning to a *different* attorney is API-only in this build:
`PATCH /api/v1/leads/{id}/assign` with `{"assignee": "…"}` (or `null` to clear).

### Curl walkthrough

Submit a lead (public, multipart — no token needed):

```bash
curl -s -X POST http://localhost:8000/api/v1/leads \
  -F "first_name=Ada" \
  -F "last_name=Lovelace" \
  -F "email=ada@example.com" \
  -F "resume=@/path/to/cv.pdf;type=application/pdf"
```
```json
{"id":"f9dfc75f-...","first_name":"Ada","last_name":"Lovelace","email":"ada@example.com",
 "resume_filename":"cv.pdf","resume_content_type":"application/pdf","state":"PENDING",
 "created_at":"2026-01-01T12:00:00Z","updated_at":"2026-01-01T12:00:00Z"}
```

Both emails are printed to the API log in console mode — look for `EMAIL (console)`.

Log in as the attorney and keep the token:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"attorney@example.com","password":"changeme"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
```

> Uses `python3` rather than `jq` so the walkthrough needs no extra tooling.
> With `jq` installed, `| jq -r .access_token` is equivalent.

List the queue, filtered and paginated (newest first):

```bash
curl -s "http://localhost:8000/api/v1/leads?state=PENDING&limit=20&offset=0" \
  -H "Authorization: Bearer $TOKEN"
```

Download a resume:

```bash
curl -s -OJ "http://localhost:8000/api/v1/leads/$LEAD_ID/resume" \
  -H "Authorization: Bearer $TOKEN"
```

Mark the lead as reached out:

```bash
curl -s -X PATCH "http://localhost:8000/api/v1/leads/$LEAD_ID/state" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"state":"REACHED_OUT"}'
```

Repeating that call returns **409** with `already_in_state` — benign, and the UI
treats it as "someone already did this" rather than an error:

```json
{"detail":"This lead is already REACHED_OUT.","code":"already_in_state"}
```

A move the pipeline forbids returns 409 with `invalid_transition` instead. The guard is
the SQL predicate `UPDATE … WHERE id = ? AND state = ?`, so of N simultaneous requests
exactly one wins.

Omitting the token on any internal route returns **401**:

```json
{"detail":"Not authenticated.","code":"not_authenticated"}
```

### Sending real email

Leave `RESEND_API_KEY` unset and every message is printed to the API log instead of
sent — that is the default, and it needs no account.

If you do set it: **Resend's free tier without a verified domain only delivers to the
address that owns the API key.** Mail to anyone else — including the fictional
`@example.com` prospects — is rejected by the provider. The rejection is logged with
the lead id and swallowed, so the lead is still created and the request still
succeeds; you will simply not receive the prospect's copy. Verify a domain, or keep
the console adapter, before reading anything into a missing email.

## Testing

```bash
make test    # pytest
make lint    # ruff check + ruff format --check + pnpm lint + tsc --noEmit
```

CI runs three jobs on every push and pull request (`.github/workflows/ci.yml`):

| Job | What it proves |
|---|---|
| `api` | ruff + the full suite on the SQLite default |
| `api-postgres` | migrations, `alembic check` and the same suite against a real `postgres:16` |
| `web` | eslint, `tsc --noEmit`, production build |

The API is stateless apart from the in-process rate-limit counters; set
`RATE_LIMIT_STORAGE_URL` to a Redis URL before running more than one replica.

## Design

See [`docs/DESIGN.md`](docs/DESIGN.md) for architecture and decisions,
[`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) for FR/NFR traceability, and
[`docs/PLAN.md`](docs/PLAN.md) for the delivery plan.

## Agent usage

See [`docs/AGENT_USAGE.md`](docs/AGENT_USAGE.md) for what was delegated to Claude Code
and what was hand-written, and [`NOTES.md`](NOTES.md) for per-file attribution.

## Demo

Screen recording link added at P2.
