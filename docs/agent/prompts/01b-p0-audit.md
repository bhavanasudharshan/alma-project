# Prompt 01b — P0 pre-commit audit: prove production readiness with evidence

> **Role reminder**: you are Claude Code, acting as auditor + tester. The planning session (architect / QA lead) wants PROOF, not assertions: for every check below paste the exact command you ran and its trimmed output, then mark PASS / FAIL / N/A. Findings you fix must be listed as separate line items with the diff summary; never fix silently. No commits, no push.

Scope: the 82 staged files (planning docs, S0 scaffold, P0 backend). `web/` has no product code yet — mark web-only checks N/A.

## A. Privacy & identity (blocker class)
1. `git diff --cached --name-only | grep -v lock | xargs grep -niE "gmail|/Users/|/home/|@[a-z0-9-]+\.(com|ai|org|net)"` — only `example.com`/`example.org` placeholders and the grep patterns inside CLAUDE.md / prompt 05 may appear. Anything else = FAIL.
2. Confirm the only personal reference anywhere is the first name "Bhavana" (docs only, never code): `git diff --cached --name-only | xargs grep -nw Bhavana`.
3. `git diff --cached --name-only | grep -E "^\.env$|(^|/)data/|(^|/)uploads/|\.db$|node_modules|\.venv|__pycache__|\.next/"` must be empty.
4. Read `git log` — should be empty (nothing committed). Confirm `git config user.name` and `user.email` are set and the email is not a personal mailbox (should be a GitHub noreply address); report the DOMAIN only, never the value.

## B. Secrets & configuration
5. `git diff --cached | grep -nE "^\+.*(key|secret|password|token)\s*[:=]" | grep -viE "example|changeme|dev-only|placeholder|test|fake|Field|settings\."` — anything remaining must be a false positive you explain.
6. Every `Settings` field appears in `.env.example` with a comment, and vice versa — script it (parse both, diff the sets). Paste the diff (must be empty).
7. Placeholder-credential guard: run the API with `ENVIRONMENT=staging` and default secrets; paste the warning line. (P1 will make it hard-fail — just prove the guard fires.)

## C. Static security & dependency hygiene
8. `uvx bandit -r api/app -ll -q` (medium+). Paste findings; each must be either fixed or justified with a `# noqa: S###` + reason.
9. `uv run ruff check --select S,B,E,F,I,UP,N,ASYNC api` (enable flake8-bandit + bugbear ad hoc). Paste count; fix or justify.
10. `uvx pip-audit` inside `api/` (or `uv export --format requirements-txt | uvx pip-audit -r /dev/stdin`). Paste vulnerable packages, if any, with fix version.
11. `cd web && pnpm audit --prod` — paste summary.

## D. Dynamic security checks against a live server (`make api` on SQLite; use curl; paste status codes)
12. **Auth bypass**: every internal route (`GET /leads`, `GET /leads/{id}`, `GET /leads/{id}/resume`, `PATCH /leads/{id}/state`) without header → 401; with `Authorization: Bearer garbage` → 401; with a token signed with a different secret → 401; with an **expired** token (mint one with exp in the past using the real secret) → 401; with `alg: none` token → 401.
13. **Login hardening**: wrong password and unknown email return identical status + body; response time for both within the same order of magnitude (paste `curl -w '%{time_total}'` for each, 3 runs).
14. **Upload abuse**: (a) 6 MB PDF → 413; (b) `.exe` renamed `.pdf` with `Content-Type: application/pdf` → what happens? Report honestly (P0 validates extension + declared type, not magic bytes — confirm and state that content sniffing is the P1/advanced item S2); (c) filename `../../etc/passwd.pdf` → 201 and the stored key is sanitised (show the on-disk path); (d) empty file → 415/422; (e) missing resume field → 422; (f) `Content-Length` spoofed smaller than the body → still 413.
15. **Injection / validation**: `first_name` of 101 chars → 422; `first_name` containing `<script>` → stored verbatim, returned JSON-escaped (no HTML rendering server-side); email `a@b` → 422; state `"DELETED"` → 422; `lead_id` `not-a-uuid` → 422 not 500.
16. **Error leakage**: trigger a 500 deliberately (e.g. temporarily point `DATABASE_URL` at an unwritable path, or monkeypatch in a test) and prove the body is the opaque envelope with no traceback; then revert.
17. **CORS**: `curl -H "Origin: https://evil.example" -I http://localhost:8000/api/v1/health` → no `Access-Control-Allow-Origin` header; with `Origin: http://localhost:3000` → header present.
18. **Resume download headers**: `Content-Disposition` is `attachment` with RFC 5987 filename; filename containing `"` and `\r\n` cannot break the header (create such a lead, download, paste raw headers).
19. **Enumeration**: `GET /leads/{random-uuid}` with valid token → 404 with generic message; confirm the body does not differ between "never existed" and "exists but resume missing" beyond what FR requires.

## E. Correctness & data integrity
20. Storage-outage path: make `uploads/` read-only, POST a lead → 503, then prove `SELECT COUNT(*) FROM leads` did not change and no email was logged. Restore permissions.
21. Concurrency on state: fire 10 parallel `PATCH … REACHED_OUT` on the same PENDING lead (`xargs -P10` or a tiny script). Exactly one 200 and nine 409 — or report the real distribution and explain (SQLite locking may serialize; state whether the `UPDATE … WHERE state = 'PENDING'` guard exists at the repository level or only in Python. If only in Python, that is a FINDING for P1: move the guard into the SQL predicate).
22. Migration round trip: fresh DB → `alembic upgrade head` → `alembic downgrade base` → `upgrade head` with no errors; `alembic check` (or `revision --autogenerate` dry run) shows no model/migration drift.
23. Test quality: `uv run pytest -q --durations=5` and paste; confirm no test hits the network or real filesystem outside tmp_path (grep tests for `requests|httpx.Client(|open(` outside fakes); paste `pytest --co -q | wc -l`.

## F. Code quality & structure
24. Layering: `grep -rn "from fastapi" api/app/services api/app/repositories api/app/core/security.py` must be empty; `grep -rn "os.environ" api/app` must be empty outside `core/config.py`.
25. Every public function/class in `api/app` has a docstring; `ruff check --select D` count (D100–D107 only) — paste the number and fix zero-cost ones.
26. Cyclomatic hot spots: `uvx radon cc api/app -n C` — paste anything ≥ C and say whether it should be split (do not refactor now).
27. Type check: `uvx mypy api/app --ignore-missing-imports` — paste error count; fix trivial ones, list the rest for P1.
28. Dead code / TODO no-ops: `grep -rnE "TODO|FIXME|XXX|pass$|NotImplementedError" api/app` — each hit justified or removed.

## G. Documentation & attribution readiness
29. `NOTES.md` file-attribution table vs `git diff --cached --name-only` (excluding lockfiles, `__init__.py`, assets): script the diff, paste it, add missing rows.
30. `NOTES.md` "Agent mistakes caught" has ≥1 P0 row that is REAL (from this audit if it produced one). If this audit found nothing, say so — do not invent.
31. README curl walkthrough: run every command in it top to bottom on a fresh DB, paste the status codes. Any drift = fix README.
32. REQUIREMENTS.md: for each ★ core row marked P0 or S0, name the test or file that evidences it. Paste as a two-column table. Rows with no evidence = FINDING.

## Report back
1. Scorecard table: `# | check | PASS/FAIL/N/A | evidence (1 line)` for all 32.
2. Findings table: `severity (blocker/should/nice) | finding | fixed now? | file` — blockers must be fixed before you finish; "should" items go to P1 unless trivial.
3. Diff summary of anything you changed (`git diff --cached --stat` before vs after).
4. Re-run `make lint && make test` at the end and paste the summary lines.
5. Verdict: "Commit-ready: YES / NO" with one sentence.
6. Questions for the architect.
