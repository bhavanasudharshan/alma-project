# Prompt 00 — Stage 0: scaffold the monorepo

> **Role reminder**: you are Claude Code, the implementer and tester. This prompt comes from the planning session (architect / product owner / QA lead), which never writes code. Scope, acceptance criteria and architecture are fixed here; implement them, test them, report back. Put any disagreement under "Questions for the architect" in your report — do not act on it.

Read `CLAUDE.md` and `docs/PLAN.md` (sections 2–4) before writing anything. This stage is Stage 0 only.

## Goal
A runnable, linted, tested skeleton with no product features yet.

## Do
1. `api/`: create a uv-managed project (Python 3.12). Deps: fastapi, uvicorn[standard], sqlalchemy>=2, alembic, pydantic>=2, pydantic-settings, python-multipart, pyjwt, passlib[bcrypt], boto3, resend, httpx (dev), pytest (dev), ruff (dev). Build the layout from PLAN §3: `app/main.py` app factory with CORS from settings, `app/core/config.py` (pydantic-settings, reads `.env` from repo root), `app/api/v1/health.py` returning `{"status":"ok"}`, `app/db/session.py` + `base.py` (SQLite default `sqlite:///./data/alma.db`), empty `repositories/`, `services/`, `schemas/` packages with `__init__.py`. Alembic initialised and wired to `settings.database_url` — no migration yet. `tests/test_health.py` passing with TestClient. `ruff.toml` (line length 100, isort enabled).
2. `web/`: `pnpm create next-app@latest web --ts --tailwind --eslint --app --src-dir=false --import-alias "@/*" --use-pnpm` (non-interactive flags). Add `lib/api.ts` exporting a typed `apiFetch` that prefixes `process.env.NEXT_PUBLIC_API_URL`. Replace the default landing page with a minimal one linking to `/apply` and `/leads` (both can 404 for now). Ensure `pnpm lint` and `pnpm tsc --noEmit` are clean.
3. Root: `Makefile` with targets `dev` (api + web concurrently), `api`, `web`, `test`, `lint`, `fmt`, `migrate`, `seed` (stub); `.env.example` with every setting in config.py commented; `.gitignore` (python, node, `.env`, `data/`, `uploads/`); `docker-compose.yml` with profiles `pg` (postgres:16, volume, healthcheck) and `s3` (minio + `mc` bucket-init sidecar) — wire nothing to them yet; `README.md` skeleton with headings: Quickstart, Full-stack mode, Configuration, API, Testing, Design, Agent usage, Demo; `docs/DESIGN.md` skeleton with headings only.
4. Run `make lint` and `make test`. Both must pass.
5. Commit in two commits: `chore(api): scaffold fastapi service` and `chore(web): scaffold next.js app + root tooling`, with trailers per CLAUDE.md (`Stage: S0`). Append rows to `NOTES.md`.

## Don't
Don't implement leads, auth, email or storage yet. Don't add a UI library. Don't push.

## Report back
Tree of created files (2 levels), the exact `make test` / `make lint` output summary, any deviation from PLAN §3 and why.
End with a section **Questions for the architect** (write "none" if none).
