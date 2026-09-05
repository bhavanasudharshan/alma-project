# Prompt 04d — P2: attorney roster + lead assignment (simplest credible slice)

> **Role reminder**: you are Claude Code, implementer + tester. Scope below is fixed and deliberately minimal — no RBAC, no auto-assignment, no attorneys table. Time box: 60 min. If the box is hit, ship what is green, revert the rest, record the deferral in NOTES.md. No commits.

## Scope
1. **Roster (no DB)**: `ATTORNEYS` setting — JSON list of `{email, password, name}`; `AttorneyDirectory` holds all of them (hash each at startup; same constant-time verify; unknown email costs a bcrypt verify). Keep `ATTORNEY_EMAIL`/`ATTORNEY_PASSWORD` working as the single-account fallback when `ATTORNEYS` is unset (default stays one login). `.env.example`: three placeholder attorneys with `@example.com` addresses and `changeme` passwords, commented. JWT unchanged (`sub` = email); add `name` claim for display.
2. **Model**: Alembic `0003_assigned_to` — nullable `leads.assigned_to` (String 320, indexed), no backfill needed. `LeadRead` gains `assigned_to` and `assigned_to_name` (resolved from the roster; null if the email is no longer in the roster — document that).
3. **API**: `PATCH /api/v1/leads/{id}/assign` body `{"assignee": "<email>" | null}`; auth; 422 if assignee not in roster; idempotent (same assignee → 200, no event); writes `lead_events` row (from `assigned_to` → to, actor = caller) in the same transaction as the update. `GET /leads` gains `?assigned_to=<email>|unassigned`.
4. **Web** (`/leads`): "Assigned to" column (name, or "—"); on unassigned rows an "Assign to me" button (server action → PATCH assign with the caller's email → revalidate); a "Mine" tab beside the state tabs (`?assigned_to=<me>`); assigned rows show the name only (reassignment is API-only in this slice — say so in the UI title tooltip and README). Header shows the attorney's name.
5. **Seed**: `make seed` assigns the demo leads across the three seeded attorneys when `ATTORNEYS` is set.
6. **Tests**: roster login for each attorney + unknown email; assign happy / reassign / unknown assignee 422 / idempotent; event row written; `assigned_to` and `unassigned` filters; `LeadRead` exposes name not password hash (grep the JSON). Update Playwright smoke: log in as attorney 1, assign, see name in column.
7. Update REQUIREMENTS.md working tree: FR10 "attorneys can assign leads to themselves and see all assignments" (evidence = tests); E-row for roster→table upgrade path. Do NOT stage .md.

## Out of scope (say so in the report if tempted)
Attorneys table, RBAC/admin, least-loaded or capacity-based auto-assign, reassignment UI, per-attorney email routing, dashboard metrics.

## Report back
Endpoint + status table, test count delta, `git diff --stat`, proposed commit `feat: attorney roster and lead assignment`, screenshots of /leads with the new column and Mine tab, "Questions for the architect".
