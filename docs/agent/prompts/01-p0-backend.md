# Prompt 01 — P0 backend: leads, state machine, auth, console email, local storage

> **Role reminder**: you are Claude Code, the implementer and tester. This prompt comes from the planning session (architect / product owner / QA lead), which never writes code. Scope, acceptance criteria and architecture are fixed here; implement them, test them, report back. Put any disagreement under "Questions for the architect" in your report — do not act on it.

Read `CLAUDE.md` and `docs/PLAN.md` §2, §4 (P0). Stage is P0. Everything must run with NO Docker.

## Domain
`Lead`: `id: UUID`, `first_name`, `last_name` (1–100 chars, stripped), `email` (validated, lowercased), `resume_key: str` (storage key), `resume_filename`, `resume_content_type`, `state: LeadState` (`PENDING` default, `REACHED_OUT`), `created_at`, `updated_at` (UTC). Index on `state` and `created_at`.

## Build
1. **Model + migration**: `app/db/models/lead.py`; Alembic revision `0001_leads`. `make migrate` applies it.
2. **Storage adapter**: `services/storage/base.py::FileStorage` Protocol with `save(key, fileobj, content_type) -> None`, `open(key) -> BinaryIO`, `delete(key)`. `services/storage/local.py::LocalDiskStorage(root=settings.upload_dir)` writing under `uploads/<uuid>/<sanitised-filename>`. Path-traversal safe.
3. **Email adapter**: `services/email/base.py::EmailService` Protocol with `send(to, subject, text, html=None)`. `services/email/console.py::ConsoleEmailService` logs the full message at INFO. `services/email/messages.py` builds the two messages: prospect confirmation (to lead.email) and attorney notification (to `settings.attorney_notify_email`, includes all lead fields + resume filename + link to internal UI). Plain-text bodies now; HTML in P1.
4. **State machine**: `services/lead_state.py` with `TRANSITIONS = {LeadState.PENDING: {LeadState.REACHED_OUT}}` and `assert_transition(current, new)` raising a domain `InvalidTransition` error → mapped to HTTP 409 in a global exception handler.
5. **Repository**: `repositories/lead_repo.py` — `create`, `get`, `list(state: Optional, limit, offset) -> (items, total)`, `update_state`.
6. **Service**: `services/lead_service.py::LeadService.create_lead(data, upload) -> Lead` validates the upload (allowed: pdf, doc, docx by content-type AND extension; max `settings.max_resume_mb`=5), stores file, persists lead in a transaction, and returns it. The router schedules the two emails with `BackgroundTasks` AFTER the DB commit (a failed email must never roll back or fail the request; log the error).
7. **Auth**: `core/security.py` — bcrypt verify, `create_access_token(sub, expires=8h)`, `decode_token`. Seeded attorney from `ATTORNEY_EMAIL` / `ATTORNEY_PASSWORD` (hash computed at startup, never stored plain). `api/v1/auth.py`: `POST /api/v1/auth/login` (JSON `{email,password}`) → `{access_token, token_type}`; 401 on bad creds. `core/deps.py::current_attorney` dependency (HTTP Bearer).
8. **Routers** (`api/v1/leads.py`), all under `/api/v1`:
   - `POST /leads` — multipart form (`first_name`, `last_name`, `email`, `resume` file). Public. 201 with `LeadRead` (no storage key exposed). 422 on validation, 413 on oversize, 415 on bad type.
   - `GET /leads?state=&limit=&offset=` — auth. Returns `{items, total, limit, offset}`, newest first.
   - `GET /leads/{id}` — auth. 404 if missing.
   - `GET /leads/{id}/resume` — auth. Streams the file with original filename and content-type.
   - `PATCH /leads/{id}/state` — auth. Body `{"state": "REACHED_OUT"}`. 409 on illegal transition. Returns updated `LeadRead`.
9. **Tests** (`api/tests/`, use fakes injected via dependency overrides, temp SQLite per test session):
   - create lead happy path → 201, file saved via `FakeStorage`, two emails captured by `FakeEmailService` with the right recipients;
   - invalid email → 422; wrong content type → 415; oversize → 413;
   - internal routes without token → 401; with bad token → 401;
   - login happy + wrong password;
   - state PENDING→REACHED_OUT → 200; REACHED_OUT→REACHED_OUT → 409; PENDING→PENDING → 409;
   - list filters by state and paginates.
10. `README.md`: fill the API section with a curl walkthrough (create lead with `-F`, login, list, patch state).
11. `make lint && make test` green. Commit: `feat(api): leads api, state machine, jwt auth, console email, local storage` with trailers (`Stage: P0`). Update `NOTES.md`.

## Constraints
Sync SQLAlchemy sessions (one per request via dependency). No business logic in routers. Do not touch `web/`. Do not push.

## Report back
Endpoint table with status codes, test summary line, anything from the spec you interpreted differently, and any place you were unsure.
End with a section **Questions for the architect** (write "none" if none).
