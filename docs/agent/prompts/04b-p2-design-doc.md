# Prompt 04b — P2: DESIGN.md as a concise, visual design guide (architecture · data flow · product)

> **Role reminder**: you are Claude Code, technical writer + diagrammer for this task. The planning session (architect) fixed the content; your job is to render it clearly and concisely from what the code actually does. Verify every claim against the repo before writing it. No code changes. No commits (MD FILES AUTHORIZED comes separately).

> Time box: 20 min. Prefer tables to prose; three diagrams total (architecture, submit sequence, state machine).

## Design principles for the document
- **Short.** Target 3–4 printed pages. Tables over prose; diagrams over tables; one sentence of prose per section to state the *why*. If a paragraph exceeds four lines, cut it.
- **Visual first.** Every architecture/flow section opens with a Mermaid diagram (GitHub renders Mermaid natively — no images to commit). Diagrams must reflect the code: node names = real module/route names.
- **Fixed decision grammar.** `Area | Driver (which requirement forced it) | Choice | Rejected alternative | Price paid`. Never a choice without its price.
- **Traceable.** Reference REQUIREMENTS.md IDs (FR1…, S1…, R1…) inline; never restate requirements at length.
- **Honest.** Mark anything deferred as *Designed, not built* with the mechanism named. Volunteer one limitation unprompted (at-most-once email).
- **No personal information.** Author referenced as "Bhavana" only; example addresses `@example.com`.

## Structure (fixed headings — keep them)

1. **Problem & scope** (≤ 8 lines) — include one labelled sentence: "Context (from Alma's public job description, not from the brief): Alma's first market is immigration law, so résumés are treated as sensitive personal data; nothing else in the design depends on this." — what Alma needs (public intake → attorney queue), in-scope FR list by ID, explicit OUT-of-scope list.
2. **Architecture** — one Mermaid `flowchart LR`: Prospect → Next.js (public) → FastAPI → [LeadService → LeadRepository → SQLite/Postgres · FileStorage → LocalDisk/S3 · EmailService → Console/Resend]; Attorney → Next.js (internal, cookie) → FastAPI (Bearer). Annotate adapters with "selected by env". Below it: the **adapter selection matrix** (env var → implementation) as a table.
3. **Request flows** — ONE Mermaid `sequenceDiagram` (submit lead, ≤ 12 messages); the other two flows as 4-row tables:
   a. Submit lead: validate → sniff → store file → commit row → 201 → background: emails (+ tracking code) — show the commit-before-email ordering and the compensating delete.
   b. Attorney marks reached out: cookie → server action → PATCH → `UPDATE … WHERE state=` → 200 / 409 `already_in_state` → event row → notify hook.
   c. Prospect checks status: tracking code → rate-limited public endpoint → state + timeline only.
4. **Data model** — Mermaid `erDiagram`: `leads`, `lead_events`; column list with types; indexes; the invariant "leads are immutable except state" and why (audit integrity).
5. **Lead state machine** — Mermaid `stateDiagram-v2` from the actual transition table (PENDING → REACHED_OUT → QUALIFIED), with `notify_prospect` marked; one line on how a state is added (E1) and the 409 code split.
6. **Decisions** — the table in the fixed grammar, 10–14 rows: db, migrations, file storage, email + timing, auth (JWT in httpOnly cookie, server-side only), state guard in SQL, error envelope, rate limiting, upload validation (sniffing, .pdf/.docx only, never rendered), config surface, monorepo, no LLM in the loop.
7. **Security & privacy** — threat → control table from REQUIREMENTS S1–S9 and SECURITY_AND_EXTENSIONS §A (what is built vs designed); PII handling (resumes private, attachment-only, redacted logs); the dev-only RSC flight-payload note with the production-build verification; the prompt/agent-injection rule for future AI features; and one sentence: no model runs inside the product by design — the problem does not call for one and it keeps the public surface free of injection risk; the AI-native investment is the agent-driven development workflow (see AGENT_USAGE.md).
8. **Operability & observability** — what is built: request-id, structured logs, health with DB check, CI gates. Then the **designed observability layer** from SECURITY_AND_EXTENSIONS.md §B2 as one table (OBS1–OBS9): product usage/trends/backlog/bottlenecks (give the actual SQL shape for submissions-per-day and median time-to-reach-out over `lead_events`), ops performance via Prometheus `/metrics`, security-flag counters at the existing rejection points (name them), `audit_events` table schema, upload histograms, Grafana/alerts with two example PromQL rules, OpenTelemetry. Mark every row *Designed, not built*. Link to README for run modes; do not duplicate.
9. **Failure modes** — table: email provider down · storage down · duplicate submit · concurrent PATCH · bad upload — current behaviour and the upgrade path (outbox, idempotency key).
10. **Scale ladder** — one horizontal line: 1x holds (single Postgres + object storage) ─► 10x: what breaks FIRST (background email on the web worker; attorney list scan) + smallest fix (worker + index) ─► 100x: shape change (queue-backed ingestion, read replica, CDN for uploads) + why the 10x fix stops working. One cost line naming the dominant driver.
11. **Roadmap — designed, not built** — one compact table from SECURITY_AND_EXTENSIONS.md: EXT3 v1.1 (built in v1: config roster + assign-to-me + Mine tab; v1.1: attorneys table, reassignment UI, least-loaded + capacity + pool policy, RBAC; race note), EXT4 load/trend dashboard (query shapes + the one index), EXT6 optional intake fields (typed enums + `extra` JSON; why all-JSON rejected), SEC2e ClamAV, SEC4 Turnstile, SEC8 idempotency, email outbox, RBAC/`sub` as stable id.
12. **One limitation** — at-most-once email; what the outbox would change.

## Companion: product quick guide (`docs/PRODUCT_GUIDE.md`, ≤ 1 page)
For a non-engineer reader: what a prospect does (apply → confirmation email with tracking code → check status), what an attorney does (log in → queue → download résumé → mark reached out → mark qualified → filters), what emails are sent when, and where to look in the demo. Three short sections, one screenshot placeholder each (`docs/img/*.png`, to be added by Bhavana from the Loom frames), no prose over five lines.

## Report back
Word count of DESIGN.md; list of diagrams with the code file each was derived from; any claim you could not verify in code (must be zero or listed); "Questions for the architect".
