# CLAUDE.md — conventions for Claude Code in this repo

## Roles — read this first
This project is run by two parties with fixed, non-overlapping roles:

| Party | Role | Does | Never does |
|---|---|---|---|
| **Planning session** (Claude, working with Bhavana) | architect · product owner · product manager · user representative · QA lead | owns `docs/PLAN.md`, `docs/REQUIREMENTS.md`, acceptance criteria, stage scope, writes the prompts in `docs/agent/prompts/`, reviews your reports, decides what is accepted and what the next stage is | writes or edits code |
| **You — Claude Code** | implementer · tester | implement exactly the stage you were given, write and run the tests and lint, commit with attribution trailers, report back precisely | change scope, pull later-stage work forward, reinterpret acceptance criteria, decide architecture (raise it in the report instead), push |

If a prompt is ambiguous or you believe a requirement is wrong, implement the narrowest reasonable reading, and put the question in your report under "Questions for the architect". Do not resolve architecture questions yourself.

Read `docs/PLAN.md` and `docs/REQUIREMENTS.md` first. When you implement something that satisfies a REQUIREMENTS.md row, reference its ID (e.g. `S1`, `R1`) in the commit body and in the test name or docstring. Work only on the stage you were asked for; do not pull later-stage work forward.

## Stack (fixed — do not substitute)
- `api/`: Python 3.12, FastAPI, SQLAlchemy 2.x (async not required; sync sessions are fine), Alembic, pydantic v2 + pydantic-settings, uv for env/deps, ruff, pytest + httpx TestClient.
- `web/`: Next.js 15 App Router, TypeScript strict, Tailwind, zod, pnpm.
- Infra: docker-compose profiles `pg` (Postgres 16) and `s3` (MinIO). Default local run must work with NO Docker (SQLite + local disk + console email).

## Architecture rules
- Layering in `api/app`: `api/v1` routers → `services` → `repositories` → `db`. Routers hold no business logic. Services never import FastAPI.
- Swappable adapters behind Protocols: `services/email/base.py::EmailService`, `services/storage/base.py::FileStorage`. Selection happens once in `core/deps.py` from settings. Tests use in-memory fakes, never real providers.
- Lead state transitions live in ONE place (`services/lead_state.py` transition table). Illegal transition → HTTP 409.
- Config only via `core/config.py` (pydantic-settings). No `os.environ` elsewhere. Every new setting goes into `.env.example` with a comment.
- Errors: consistent JSON envelope `{"detail": ..., "code": ...}`; never leak stack traces.
- Web: server components fetch the API with the JWT read from the httpOnly cookie; client components never see the token. `middleware.ts` guards `/leads`.

## Quality gates before every commit
```
make lint    # ruff check + ruff format --check + pnpm lint + tsc --noEmit
make test    # pytest
```
Both must pass. If you cannot make them pass, stop and report — do not commit red.

## Commits (mandatory format)
Conventional commits, one logical change per commit, and ALWAYS these trailers:
```
<type>(<scope>): <summary>

<what and why, 1-4 lines>

Agent: claude-code
Author-mode: agent-generated        # or: agent-assisted | hand-written
Review: gates                       # or: architect-accepted | adversarial-audit(<prompt id>) — comma-separate when several apply
Stage: S0 | P0 | P1 | P2
```
**Markdown gate (absolute)**: NO `.md` file anywhere in the repo may be included in any commit unless the kickoff message from the planning session lists that file by exact path under the heading "MD FILES AUTHORIZED". This includes README.md, NOTES.md, CLAUDE.md, docs/**, and web/*.md. Stage code by explicit path (`git add api/ web/ Makefile docker-compose.yml .env.example .gitignore` etc.), never `git add -A` or `git add .`. Before every commit run `git diff --cached --name-only | grep -i '\.md$'` and it must print only authorized paths; otherwise unstage the rest and say so in the report -- `git restore --staged <paths>` once a first commit exists, or `git rm --cached -f <paths>` before it (in a repo with no HEAD `git restore --staged` fails with "could not resolve HEAD" and silently changes nothing; `git rm --cached` leaves the file on disk either way). Keep NOTES.md up to date in the working tree as before — it is simply not committed until authorized.

**Commit gate**: commit ONLY when the kickoff message from the planning session explicitly says "commits authorized". Otherwise do NOT commit: leave changes in the working tree, run `git add -A` so they are staged, and put the exact commit message(s) you WOULD have used (with trailers) in your report under "Proposed commits". Bhavana reviews first; commits happen after approval. `Review:` values — `gates` = lint+tests only; `architect-accepted` = the planning session reviewed the report and accepted; `adversarial-audit(01b)` = passed a proof-based audit prompt (name it). Never claim a review that did not happen.

Never amend or rewrite history. Never `git push` unless the prompt says so.

## Attribution log
Append a row to `NOTES.md` for every file you create or substantially rewrite: `path | mode | stage | note`. If you notice you made a mistake that was caught (by tests, by review, by the user), record it in the "Agent mistakes caught" section of `NOTES.md` — these are required for the submission writeup.

## Don'ts
- No new dependencies beyond the stack above without stating why in the commit body.
- No secrets in the repo. `.env` is gitignored; `.env.example` has placeholders.
- No placeholder/TODO code paths that silently no-op. If something is out of scope, raise `NotImplementedError` with a message, and say so in your final report.
- Do not fabricate test results; run them and paste the summary in your final message.

## Privacy (mandatory)
The human author is referred to by first name only: **Bhavana**. Work is attributed as "Bhavana" (hand-written / decisions) and "Claude" or "Claude Code" (agent). Beyond that first name, NO personal information anywhere in the repo — no surnames, email addresses, home-directory paths, phone numbers, or other identifiers — in docs, code, comments, seed data, fixtures, or transcripts. Use neutral placeholders (`attorney@example.com`, `/path/to/repo`). Before every commit run: `git grep -niE "gmail|Users/|/home/" -- . ':!*.lock'` and it must return nothing. Session transcripts saved to `docs/agent/sessions/` must be redacted the same way. `docs/private/` and `docs/agent/sessions/*.raw.md` are gitignored and must never be force-added. **Any new or modified `.md` file is committed only when the kickoff message names it explicitly** — never sweep docs into a code commit with `git add -A`; stage code paths by name.
