# Prompt 03 — P1: production hardening (S3/MinIO, Resend, Postgres, CI)

> **Role reminder**: you are Claude Code, the implementer and tester. This prompt comes from the planning session (architect / product owner / QA lead), which never writes code. Scope, acceptance criteria and architecture are fixed here; implement them, test them, report back. Put any disagreement under "Questions for the architect" in your report — do not act on it.

Read `CLAUDE.md`, `docs/PLAN.md` §2/§4 (P1). Stage is P1. Default no-Docker mode must keep working unchanged.

## Build
1. **S3 storage**: `services/storage/s3.py::S3Storage` (boto3) implementing `FileStorage`; selected in `core/deps.py` when `S3_ENDPOINT_URL` (or `S3_BUCKET` with AWS creds) is set, else `LocalDiskStorage`. Ensure bucket exists at startup (lifespan) when using MinIO. Resume download: keep the authenticated proxy stream (works for both backends); add `presigned_url(key, expires)` to the Protocol as optional (return `None` for local) and use it in the API response as `resume_url` only when available. Wire `docker-compose --profile s3` (MinIO + bucket-init) and document `.env` values.
2. **Resend email**: `services/email/resend.py::ResendEmailService` selected when `RESEND_API_KEY` set. Add HTML templates (Jinja2 or simple f-strings in `services/email/templates/`) for both messages with a text fallback. `EMAIL_FROM` setting. Provider errors are logged with the lead id, never raised to the request.
3. **Postgres**: `docker compose --profile pg up` + `DATABASE_URL=postgresql+psycopg://…` (add `psycopg[binary]`). Run Alembic against Postgres and fix any SQLite-only assumptions (UUID type, server defaults, timezone).
4. **Cross-cutting**: request-id middleware (`X-Request-ID` in/out, in logs), structured JSON logging toggle, global exception handlers → error envelope, CORS allow-list from settings, `/api/v1/health` reports db connectivity, OpenAPI tags + response examples.
4b. **Public-surface hardening (approved — read docs/SECURITY_AND_EXTENSIONS.md §A)**:
   - SEC1: `slowapi` per-IP limits — `POST /leads` 5/10min, `POST /auth/login` 10/5min, 429 with `Retry-After`; limiter storage in-memory now, `RATE_LIMIT_STORAGE_URL` setting for Redis later. Tests: 6th request → 429.
   - SEC2: magic-byte sniffing (`filetype` or `python-magic`) must agree with extension AND declared type; accept `.pdf` and `.docx` only (drop `.doc`, update tests + README + web accept list); resume download adds `X-Content-Type-Options: nosniff`. Test: `.exe` bytes as `.pdf` → 415.
   - SEC3: email templates via Jinja2 with autoescape; strip CR/LF from subjects; test that a `<script>` first name is escaped in the attorney HTML email. Add a DESIGN.md §7 bullet stub (working tree) "no LLM reads lead data; injection rule for future AI features".
   - SEC4: honeypot field `website` on the form and API — non-empty → 202 with no lead created (silent drop, logged).
   - SEC6: security headers — FastAPI middleware (`nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, CSP `default-src 'none'` for the API); Next `headers()` (CSP self, frame-ancestors none, nosniff, referrer). HSTS only when `ENVIRONMENT != local`.
   - SEC9-lite: `lead_events` table (id, lead_id FK, from_state, to_state, actor, created_at) written in the same transaction as every state change; Alembic `0002`. Expose as `events` list on `GET /leads/{id}` only.
   - EXT1 column: `tracking_code` (unique, ≥128-bit, base32, generated in the service at create), included in the prospect confirmation email as "Your tracking code". Not yet queryable publicly.
   - EXT2 flag: transition table entries become `{to_state: TransitionRule(notify_prospect: bool)}`; REACHED_OUT has `notify_prospect=True`; no sends wired yet.
   - Also: `send_intake_emails` takes a plain `LeadSnapshot` dataclass, not the ORM instance; console email logs recipient + subject + lead id at INFO and the body at DEBUG; startup hard-fails on placeholder secrets when `ENVIRONMENT != local`.
5. **CI**: `.github/workflows/ci.yml` — job `api` (uv sync, ruff, pytest) and job `web` (pnpm install --frozen-lockfile, lint, tsc, build). Cache deps.
6. **Tests**: `S3Storage` via `moto` (dev dep) — save/open/delete round trip; email template renders both messages with all fields; health endpoint; request-id echoed.
7. Verify: (a) no-Docker mode `make test` + manual E2E; (b) `docker compose --profile pg --profile s3 up -d` then `make migrate && make dev` and repeat E2E — resume opens from MinIO, email goes to Resend if key present else console. Paste observations.
8. `make lint && make test` green. Commit as 2–3 logical commits (`feat(api): s3 storage adapter + minio profile`, `feat(api): resend email adapter + html templates`, `chore: postgres profile, observability, ci`) with trailers (`Stage: P1`). Update `NOTES.md`, including any mistake you caught in your own P0 code.

## Don't
No new frontend features (only adjust `web/` if `resume_url` changes the contract). Do not push.

## Report back
Adapter selection matrix (env → chosen impl), any SQLite→Postgres fixes you had to make, CI status locally simulated.
End with a section **Questions for the architect** (write "none" if none).
