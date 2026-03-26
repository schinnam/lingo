# Lingo — TODOS

## P1

### Transactional vote + status transition
**What:** Wrap vote insert + status check + status update in a single DB transaction with row lock.
**Why:** Two concurrent votes can both pass the threshold check simultaneously, resulting in duplicate status transitions or a corrupted vote count.
**Pros:** Prevents silent data corruption; trivial to implement at the right time.
**Cons:** None — this is correctness, not an optimization.
**Context:** The `POST /api/v1/terms/:id/vote` endpoint must use a Postgres transaction with `SELECT ... FOR UPDATE` on the Term row, then insert Vote (composite PK dedupes), then recount and conditionally update status. Must be accompanied by a goroutine concurrency test (TestVoteConcurrentAtThreshold) that fires 5 concurrent votes at threshold boundary and asserts exactly 1 transition fires. See test plan for full test spec.
**Effort:** S → CC: S
**Priority:** P1
**Depends on:** Vote endpoint implementation

---

## P2

### Export pagination / size cap
**What:** Add a 500-term cap to `GET /api/v1/export` with a `Lingo-Truncated: true` response header and `?offset=` pagination param.
**Why:** A company with 500+ Official terms will get a multi-MB response or a timeout. The cap is a trivial safeguard.
**Pros:** Prevents timeout on large glossaries; adds streaming/pagination foundation.
**Cons:** None significant.
**Context:** For v1, most deployments won't hit 500 Official terms. But the cap should be in place before a company with a large legacy glossary imports terms. The CLI and Slack bot use the default limit. Power users paginate manually. Future: streaming export (v3).
**Effort:** S → CC: S
**Priority:** P2
**Depends on:** Export endpoint implementation

---

## P2 (Deferred from Scope Expansion)

### PDF Export
**What:** `GET /api/v1/export?format=pdf` — server-side PDF generation of the Official glossary.
**Why:** Some teams want a printable PDF for onboarding packets or all-hands distribution.
**Pros:** Completes the export story; satisfies "send me a PDF" requests.
**Cons:** Requires Puppeteer or pdf-lib — adds non-trivial binary weight to the Docker image (+150MB+ for Puppeteer). Markdown covers 90% of the use case.
**Context:** Deferred because markdown export is zero-cost and solves the primary use case. PDF is valuable for onboarding packets where the recipient doesn't have access to Lingo yet. When ready: use `markdown-pdf` (lighter) or `@jsreport/nodejs-client` for server-side rendering. Must be behind a feature flag initially.
**Effort:** S → CC: S
**Priority:** P2
**Depends on:** Export endpoint (markdown) already shipping

---

---

## P2

### Audit Log
**What:** An `AuditEvent` table recording who did what, when — term deletions, role changes, status transitions, bootstrap token use.
**Why:** Editors can delete terms and admins can reassign roles with no record of who did it. Enterprise self-hosters expect an audit trail. Adding this retroactively means all early actions are untracked.
**Pros:** Required for enterprise buyers; enables incident investigation; no behavioral change to existing APIs (append-only side effect).
**Cons:** Adds write overhead on every mutation; schema migration required if added post-launch.
**Context:** Minimum schema: `{ id, actor_id FK→User, action text, target_type text, target_id uuid, payload jsonb, created_at timestamptz }`. Actions: term.created, term.updated, term.deleted, term.official, vote.cast, user.role_changed, token.created, token.revoked, setup.completed. Wire as a post-commit hook in the API handlers, not in the DB transaction (avoids slowing mutations). If added in v1, all actions are captured from day 1.
**Effort:** M → CC: ~20 min
**Priority:** P2
**Depends on:** REST API implementation

---

## P2

### CLI JSON output flag (`--json`)
**What:** Add `--json` flag to `lingo define`, `lingo search`, and `lingo list` commands for machine-readable output.
**Why:** Enables scripting, automation, and shell pipelines that consume term data without parsing human-formatted output.
**Pros:** Trivial to implement — CLI already calls the API; just serialize response as JSON to stdout.
**Cons:** None significant.
**Context:** MCP already provides machine-readable access for AI agents. This is for shell scripting use cases (e.g., `lingo define BART --json | jq .status`). Add at the same time as CLI implementation to avoid retrofitting.
**Effort:** S → CC: ~5 min
**Priority:** P2
**Depends on:** CLI implementation

---

## P2

### Slack BlockKit message templates
**What:** Design and implement Slack BlockKit JSON templates for all DM/channel notifications: staleness confirmation, dispute notification, promotion confirmation (to source channel), and admin "Needs Review" alert.
**Why:** Without BlockKit, all Slack messages are plain text with no interactive buttons. Users won't see [Confirm] / [Update] / [View in Lingo] buttons — they'll have to type commands manually.
**Pros:** BlockKit buttons dramatically improve response rate on staleness confirmations. Channel promotion messages with a "View in Lingo" button drive adoption.
**Cons:** BlockKit JSON adds ~50 lines per message template. Must be tested in a Slack workspace.
**Context:** Functional message structure is specified in the plan (what each message says). BlockKit specifies the interactive layer (buttons, sections, overflow menus). Each message needs a fallback text for Slack clients that don't support BlockKit. Minimum templates: staleness DM (with Confirm/Update/Delete buttons), dispute DM (with View Term link), promotion channel message (with View in Lingo link), admin unowned-stale alert.
**Effort:** M → CC: ~15 min
**Priority:** P2
**Depends on:** Slack Socket Mode implementation, LingoStalenessJob

---

## Notes

Items considered and skipped:
- **Proactive Slack Detection** (📖 emoji reaction): Requires `message.channels` Slack event subscription + in-memory term cache. Skipped — command-based lookup is sufficient and passive monitoring adds noise risk. Revisit if users request it post-launch.
