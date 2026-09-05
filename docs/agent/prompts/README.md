# Prompt pack — one Claude Code session per stage

| # | file | stage | expected commits | producing commits (fill at P2) |
|---|---|---|---|---|
| 00 | 00-scaffold.md | S0 | chore(api), chore(web) | |
| 01 | 01-p0-backend.md | P0 | feat(api) | |
| 01b | 01b-p0-audit.md | P0 | none (audit report; fixes fold into feat(api)) | |
| 02 | 02-p0-frontend.md | P0 | feat(web) | |
| 03 | 03-p1-hardening.md | P1 | feat(api) ×2, chore | |
| 04 | 04-p2-docs.md | P2 | test(web) e2e, docs | |
| 04d | 04d-p2-assignment.md | P2 | feat | |
| 04e | 04e-p2-web-tests.md | P2 | test(web) | |
| 04c | 04c-p2-ui-polish.md | P2 | style(web) | |
| 04b | 04b-p2-design-doc.md | P2 | none (docs; MD authorization separate) | |
| 05 | 05-p2-review.md | P2 | none (report) | |

Outputs that are documents rather than commits: **04b** produced `docs/DESIGN.md` (full rewrite of
the S0 skeleton) and `docs/PRODUCT_GUIDE.md` (new). Both sit unstaged until an MD authorization
names them.

Run from repo root: `claude "$(cat docs/agent/prompts/00-scaffold.md)"` — or start `claude` and paste the file.
After each session save an excerpt to `docs/agent/sessions/NN-*.md` (see the template there).
