# UI concepts — landing, intake, confirmation, status (design pass, zero functional change)

> Status: CONCEPT for Bhavana's approval. Rule: no new routes, fields, API calls, validation rules or behaviour. Copy, layout, hierarchy, colour, spacing only. Every change carries its justification. Vocabulary stays at the assignment's level (lead, prospective client, attorney, résumé) — no domain claims about Alma's practice area.

## Principles
1. **First-visit clarity** — a first-time visitor understands in 5 seconds what this is, what to do, and what happens next.
2. **Match the brief's look** — the assignment PDF is white with a deep-green wordmark. Move from the dev-default dark theme to a light theme with a single green accent. *Why:* the screenshots and Loom will sit next to that PDF; matching it reads as attention to the client. *Note:* the wordmark is rendered as plain lowercase text "alma" in the accent colour — we do not reproduce the logo artwork.
3. **One accent, one typeface, generous whitespace** — Tailwind defaults, no component library, no images/illustrations. *Why:* zero dependencies, zero scope creep, fast to implement, looks deliberate.
4. **Say what the system does, not what the firm does** — copy describes the intake service only.

## Palette & type (tokens only)
| Token | Value | Use |
|---|---|---|
| `--brand` | deep green ≈ `#1F4D2B` | wordmark, primary button, active tab, focus ring |
| `--brand-soft` | `#E8F1EA` | badges/tint backgrounds |
| `--ink` | `#111827` | body text |
| `--muted` | `#6B7280` | helper text |
| `--surface` | `#FFFFFF` / `#F9FAFB` | page / cards |
| States | PENDING amber `#B45309` · REACHED_OUT green `#166534` · QUALIFIED blue `#1D4ED8` | badges, unchanged semantics |
Type: system sans (already in globals.css), 3 sizes only (32/18/14).

## 1. Landing page `/` — "contact-us" shape, still just two links
Structure (top → bottom), max-width 720px, centred:
1. **Header**: wordmark "alma" (left) · "Attorney sign in" (right, quiet text link). *Why:* attorneys are the secondary audience; keep their entry visible but out of the prospect's way.
2. **Hero**: H1 "Lead intake" · one sentence: "Prospective clients submit their details and résumé; an attorney reviews each submission and reaches out." · primary button "Apply" → `/apply`. *Why:* spec vocabulary, verb-first.
3. **How it works** (3 short columns, numbered): ① Submit your details and résumé · ② You receive a confirmation email with a tracking code · ③ An attorney reviews and reaches out; check progress any time on the status page. *Why:* sets expectations, surfaces the tracking-code feature so the demo flow is discoverable; every claim maps to built behaviour.
4. **Before you start** (small card): "You'll need: your name, an email address you check, and your résumé as PDF or DOCX (up to 5 MB)." *Why:* reduces failed submissions; mirrors the real validation rules exactly.
5. **Footer**: "Have a tracking code? Check your status →" (`/status`) · small privacy line: "Your résumé is stored privately and is only visible to attorneys reviewing your submission." *Why:* true of the implementation (attachment-only, authenticated download); reassures without over-promising.
Removed: "Scaffold only…" developer text. No other elements.

## 2. Intake page `/apply` — same fields, clearer form
1. **Header** as above (wordmark, quiet sign-in link).
2. **Title** "Apply" · sub-line "Takes about two minutes. Fields marked * are required." *Why:* all four fields are required by spec; say so once.
3. **Card** with fields in two groups:
   - *About you*: First name*, Last name* (side by side ≥ 640px), Email* with helper "We'll send your confirmation and tracking code here." *Why:* helper explains why the email matters — fewer typos.
   - *Your résumé*: single drop-zone-styled file input (still a plain `<input type=file>` underneath) showing accepted types and limit "PDF or DOCX, up to 5 MB", and the chosen filename once selected. *Why:* the #1 failure path is wrong type/size; the rule is visible before the click. No drag-drop JS added — styling only.
4. **Submit** primary button "Submit application"; disabled + "Submitting…" while pending (existing behaviour, restyled). Errors: field-level in red beneath the field (existing), form-level banner above the button (existing).
5. **Below the button**: the same one-line privacy note as the landing footer. *Why:* consent-adjacent context at the moment of upload.
Honeypot field stays visually hidden exactly as implemented.

## 3. Confirmation `/thank-you`
Wordmark · check-mark glyph (CSS, no image) · H1 "Thanks — we've received your application." · **Tracking code shown large in a copyable monospace block** with "Save this code to check your status later." · secondary button "Check status" → `/status` · muted line "A confirmation email is on its way." *Why:* the code is the one thing the prospect must keep; make it impossible to miss. (Requires the code to be available on this page — if the current redirect does not pass it, the page shows only the email line; NO new API call is added for this pass.)

## 4. Status page `/status` (P2 feature, styled the same way)
Single input "Tracking code" + button "Check status" · result card: current state badge, submitted date, timeline of events (dot list). Empty/unknown: "We couldn't find that code. Check your confirmation email." *Why:* one screen, one action, no PII displayed — matches the endpoint contract.

## 5. Internal pages `/login`, `/leads` — light theme only
Apply the palette and header; keep table, tabs, badges, buttons and pagination exactly as they are. Add one line under the "Leads" title: "Newest first. Mark a lead after you have reached out." *Why:* consistency; the attorney UI already works and is not the reviewer's first impression.

## Out of scope (explicitly)
New pages, marketing content about the firm, images/logo assets, animations, dark-mode toggle, i18n, analytics, any change to forms' fields, validation, routes, API calls or server actions.

## Acceptance for the implementing prompt
- `git diff --stat` touches only `web/app/**/page.tsx`, layouts, `globals.css`, `components/*` presentational files; **no** change to `actions.ts`, `lib/api.ts`, `lib/validation.ts`, `middleware.ts`, route handlers, or anything under `api/`.
- Playwright smoke still green; `pnpm lint`, `tsc` clean.
- Screenshot of each page attached to the report.
