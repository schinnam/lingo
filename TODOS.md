# Lingo — TODOS

## P0 — Adversarial Review: Phase 7 Web UI (2026-03-26)

### #1 API shape mismatch — term list always empty in production
**File:** `frontend/src/api/terms.ts:14`, `src/lingo/api/routes/terms.py:73`
**Impact:** Frontend expects `{ items, total, offset, limit }` but backend returns bare `Term[]`. `data?.items` is always `undefined`. Term list shows empty on every page load — silent production outage.
**Fix:** Add `TermsListResponse` schema to backend and return it, OR change frontend types to expect `Term[]` directly.
**Priority:** P0
**Completed:** 2026-03-26 — Added `TermsListResponse` to backend schema; updated `list_terms` to return paginated envelope. Also added `counts_by_status` to fix #2.

---

### #12 X-User-Id header — unconditional auth bypass
**File:** `src/lingo/api/deps.py:107-118`
**Impact:** Any caller who knows a valid UUID can impersonate any user in production. `owner_id` is returned in every `TermResponse`. No `settings.dev_mode` gate.
**Fix:** Gate the `X-User-Id` bypass behind `if settings.dev_mode:`.
**Priority:** P0
**Completed:** 2026-03-26 — Gated X-User-Id behind `settings.dev_mode`; tests updated to set `dev_mode=True`.

---

### #3 TypeError in TermDetail — relationships always undefined
**File:** `frontend/src/components/TermDetail.tsx:47`
**Impact:** `term.relationships.length` throws TypeError — backend doesn't include `relationships` in `TermResponse`. Detail panel crashes on every open.
**Fix:** Guard with `term.relationships ?? []` OR add `relationships` field to the backend `TermDetail` endpoint.
**Priority:** P0
**Completed:** 2026-03-26 — Guarded with `term.relationships ?? []` in both `.length` check and `.map()` call.

---

### #6 Form state never resets on modal cancel
**File:** `frontend/src/components/AddTermModal.tsx:43-48`
**Impact:** Open modal, fill fields, click Cancel — stale values + validation errors reappear on next open.
**Fix:** Call `resetForm()` in the Cancel handler.
**Priority:** P1
**Completed:** 2026-03-26 — Cancel handler now clears all fields and errors before calling `onClose()`.

---

### #2 Status filter counts wrong under pagination
**File:** `frontend/src/App.tsx:34-40`
**Impact:** Per-status counts computed only over current page (≤100). Shows "Official (0)" when 400 exist on later pages.
**Fix:** Fetch per-status counts from backend or use separate count queries.
**Priority:** P1
**Completed:** 2026-03-26 — Backend now returns `counts_by_status` in `TermsListResponse`; frontend uses that instead of filtering current page items.

---

### #10 Alembic downgrade leaves orphan enum types
**File:** `alembic/versions/2277c37b0174_initial_schema.py:118-127`
**Impact:** Re-running upgrade after downgrade fails with `ERROR: type "jobtype" already exists`.
**Fix:** Add `op.execute("DROP TYPE IF EXISTS jobtype, jobstatus, relationshiptype")` in `downgrade()`.
**Priority:** P1
**Completed:** 2026-03-26 — Added `DROP TYPE IF EXISTS` for all three enum types in `downgrade()`.

---

### #14 GET /api/v1/export unauthenticated — bulk extraction
**File:** `src/lingo/api/routes/export.py:12`
**Impact:** The export endpoint has no auth dependency (`SessionDep` only). Any unauthenticated caller can paginate through the entire glossary with no token required. Every other write endpoint requires `CurrentUser`.
**Fix:** Add `current_user: CurrentUser` to `export_terms` function signature.
**Priority:** P2

---

### #15 Container runs as root — no USER directive in Dockerfile
**File:** `Dockerfile`
**Impact:** No `USER` directive — the FastAPI process runs as UID 0. Maximizes blast radius of any future RCE (full filesystem read/write inside container).
**Fix:** Add before CMD: `RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app` then `USER appuser`.
**Priority:** P2

---

### #16 No CORS configuration
**File:** `src/lingo/main.py`
**Impact:** FastAPI with no `CORSMiddleware` is a future footgun. When someone adds CORS to unblock a frontend integration, `allow_origins=["*"]` is the path of least resistance and opens cross-origin attacks.
**Fix:** Add `CORSMiddleware` with `allow_origins=[settings.app_url]` before the app needs it.
**Priority:** P2
**Completed:** v0.5.3 (2026-03-26)

---

### #4 Dispute endpoint is a silent no-op
**File:** `src/lingo/api/routes/terms.py:164-177`
**Impact:** `POST /terms/{id}/dispute` sets no flag, sends no notification. User action silently discarded.
**Fix:** Implement dispute tracking. At minimum, add UI feedback ("dispute recorded").
**Priority:** P2

---

### #5 voteTerm return type mismatch
**File:** `frontend/src/api/terms.ts:28`
**Impact:** Typed as `Promise<Term>` but backend returns `{ vote_count, transition }`. Silent type lie.
**Fix:** Align types — add `VoteResponse` frontend type.
**Priority:** P2

---

### #7 Double-submit race in AddTermModal
**File:** `frontend/src/components/AddTermModal.tsx:40`
**Impact:** Fast double-click fires two POST requests before re-render sets `submitting=true`.
**Fix:** Use `addTerm.isPending` (synchronous) instead of `submitting` state.
**Priority:** P2

---

### #8 index.html read from disk on every request
**File:** `src/lingo/main.py:74`
**Impact:** Under load, disk read per page load degrades performance.
**Fix:** Cache `index.read_text()` at startup.
**Priority:** P2

---

### #9 Dev mode meta injection fragile
**File:** `src/lingo/main.py:76-78`
**Impact:** If `</head>` appears elsewhere or as `</HEAD>`, injection silently fails or fires twice.
**Fix:** Use a placeholder comment in `index.html` to target injection.
**Priority:** P2

---

### #11 Nullable auth columns in tokens table
**File:** `alembic/versions/2277c37b0174_initial_schema.py:163-174`
**Impact:** `user_id` and `token_hash` nullable — orphaned tokens can exist with no DB constraint.
**Fix:** Add `nullable=False` to `token_hash` and `user_id`.
**Priority:** P2

---

### #13 Keyboard shortcut guard misses contenteditable/select
**File:** `frontend/src/App.tsx:44-47`
**Impact:** Pressing `/` in a rich text editor focuses the search bar.
**Fix:** Add `isContentEditable` and `SELECT` checks to the `isInput` guard.
**Priority:** P2

---

## P1

### Transactional vote + status transition
**What:** Wrap vote insert + status check + status update in a single DB transaction with row lock.
**Why:** Two concurrent votes can both pass the threshold check simultaneously, resulting in duplicate status transitions or a corrupted vote count.
**Pros:** Prevents silent data corruption; trivial to implement at the right time.
**Cons:** None — this is correctness, not an optimization.
**Context:** The `POST /api/v1/terms/:id/vote` endpoint must use a transaction with: (1) INSERT vote row — composite PK raises IntegrityError for duplicate vote; (2) COUNT votes for the term; (3) conditional CAS UPDATE: `UPDATE terms SET status=$new, version=version+1 WHERE id=$id AND version=$current_version AND (SELECT COUNT(*) FROM votes WHERE term_id=$id) >= threshold`. **Do NOT use `SELECT FOR UPDATE` on the terms row** — this creates deadlock with optimistic locking on term edits. Must be accompanied by an async concurrency test (`test_vote_concurrent_at_threshold`) that fires 5 concurrent `asyncio` tasks at threshold boundary and asserts exactly 1 status transition fires. See test plan for full test spec.
**Effort:** S → CC: S
**Priority:** P1
**Depends on:** Vote endpoint implementation
**Completed:** v0.5.2 (2026-03-26) — Implemented CAS `UPDATE terms SET status=?, version=version+1 WHERE id=? AND status=? AND version=?`. Added `test_vote_concurrent_at_threshold` using `asyncio.gather` with two sessions racing at threshold.

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
**Completed:** v0.2.0 (2026-03-26) — staleness DM uses Block Kit with Confirm/Update buttons; dispute and promotion use plain text (no interactive actions needed)

---

## P2

### K8s multi-replica job locking
**What:** Implement Postgres advisory lock (`pg_try_advisory_lock`) at the start of LingoDiscoveryJob and LingoStalenessJob to ensure only 1 replica fires each job in multi-replica Kubernetes deployments.
**Why:** APScheduler `--workers 1` prevents duplicates in docker-compose, but K8s with `replicaCount > 1` will fire jobs once per pod — resulting in duplicate Slack DMs to term owners.
**Pros:** Safe horizontal scaling without Redis; ~20 lines per job; `pg_try_advisory_lock` is always available in Postgres.
**Cons:** Advisory locks don't survive Postgres restarts (fine since jobs are periodic and will re-acquire on next schedule tick).
**Context:** v1 is docker-compose-first with the `--workers 1` constraint documented in Resolved Design Decisions #8. This is a v2 item for enterprise K8s users who need >1 replica. Pattern: `SELECT pg_try_advisory_lock(hashtext('lingo_discovery_job'))` at job start, `pg_advisory_unlock(...)` at end. If lock not acquired, skip execution.
**Effort:** S → CC: ~15 min
**Priority:** P2
**Depends on:** Job implementation

---

## P2

### Dependency version audit (pre-release)
**What:** Before cutting v1.0: pin major versions of key dependencies, run `uv lock --upgrade`, check security advisories, verify license compatibility.
**Why:** Several stack dependencies were chosen based on 2025-2026 best practices and may have unstable APIs: `fastmcp` (new library), `apscheduler` (must pin `>=3.10,<4.0` — v4.0 is beta), `mcp` (pin `>=1.6` for Streamable HTTP). Unpinned deps in Docker images cause production breakage on self-hosted tools.
**Pros:** Prevents "it worked in dev, broke in prod" for Docker image users; catches upstream security advisories before release.
**Cons:** Time-sensitive (dependencies change). Do as last step before tagging v1.0.
**Context:** `uv.lock` pins transitive deps, but `pyproject.toml` version constraints need explicit major-version pins. Minimum: `apscheduler>=3.10,<4.0`, `mcp>=1.6,<2.0`, `authlib>=1.3`, `fastmcp>=0.1`. Also run `pip-audit` or `uv run pip-audit` for CVEs.
**Effort:** S → CC: ~10 min
**Priority:** P2
**Depends on:** All feature implementation

---

## P2

### LingoDiscoveryJob message-level cursor checkpointing
**What:** Change `progress_json` cursor to track both `channel_id` AND `message_cursor` (Slack's `next_cursor` pagination token within a channel), not just channel index.
**Why:** Current channel-level cursor means a crash mid-channel causes the entire channel to be re-scanned, potentially creating duplicate `suggested` terms for the same acronyms. The deduplication logic (update `occurrences_count` if name exists) mitigates this but the DB is still hit redundantly.
**Pros:** True resumability; no re-scanning on restart; no duplicate DB writes.
**Cons:** progress_json schema becomes more complex (dict of channel_id → message_cursor instead of a channel index integer).
**Context:** `progress_json` format change: `{"channels_done": N, "channels_total": N, "current_channel_cursor": "abc123"}` → `{"channels_done": N, "channels_total": N, "channel_cursors": {"C0123": "xyz789", ...}}`. The job must checkpoint every N messages (suggest N=100 to limit re-scan on restart).
**Effort:** S → CC: ~15 min
**Priority:** P2
**Depends on:** LingoDiscoveryJob implementation

---

## P2

### Socket Mode event recovery across restart window
**What:** Document and implement a recovery strategy for the ~30s Slack event queue window during process restart (deploy, crash, OOM).
**Why:** When the Uvicorn process restarts, Slack queues events for ~30 seconds before dropping them. `/lingo define` commands sent during a deploy are silently lost. The `asyncio.shield` pattern only prevents mid-handler cancellation, not event loss during reconnect.
**Pros:** Users don't silently get no response to Slack commands during deployments.
**Cons:** Full recovery requires at-least-once delivery semantics (idempotent handlers) which adds complexity.
**Context:** Two pragmatic options: (1) Accept the 30s window as documented behavior; note it in the operator guide as "commands sent during deployment may be lost"; (2) Implement idempotent handlers that check `event_id` against a Redis/DB dedup set and silently skip already-processed events. Option 1 is v1. Option 2 is v2.
**Effort:** M → CC: ~20 min
**Priority:** P2
**Depends on:** Slack Socket Mode implementation

---

## P2

### APScheduler SQLAlchemy job store for crash-resilient discovery
**What:** Configure APScheduler to use `SQLAlchemyJobStore` (Postgres) instead of the default `MemoryJobStore`, so job schedules survive process restarts.
**Why:** With `MemoryJobStore`, a process restart during `LingoDiscoveryJob` loses the scheduler state. The DB `Job.progress_json` cursor is only useful if the job itself checkpoints it periodically — but the scheduler doesn't know to resume an interrupted job.
**Pros:** Surviving restarts is especially valuable for LingoDiscoveryJob (can take minutes on large workspaces). `SQLAlchemyJobStore` uses the existing Postgres connection.
**Cons:** APScheduler's SQLAlchemy job store uses a separate sync SQLAlchemy engine (not the async one). Requires a separate sync engine for the job store. Adds ~10 lines of config.
**Context:** `SQLAlchemyJobStore(url=DATABASE_URL_SYNC)` — note: must use `postgresql://` (sync) not `postgresql+asyncpg://` for this specific integration. The async app engine and the APScheduler job store engine are separate.
**Effort:** S → CC: ~15 min
**Priority:** P2
**Depends on:** APScheduler implementation

---

## P2

### Startup assertion: single-worker enforcement
**What:** Add a startup check that warns (or errors) if the app detects it's running in a multi-worker context with the scheduler enabled.
**Why:** `--workers 1` is documented but not enforced. An operator who bumps workers for a traffic spike unknowingly creates duplicate scheduled jobs (duplicate Slack DMs, duplicate discovery runs).
**Pros:** Prevents silent duplicate behavior. Self-documenting constraint.
**Cons:** Detecting worker count from inside the process is not directly supported by Uvicorn's API. Workaround: check for a `LINGO_SCHEDULER_ENABLED` env var that defaults to `true`; set `LINGO_SCHEDULER_ENABLED=false` on worker processes beyond the first (requires a custom Uvicorn worker class or wrapper script).
**Context:** Simplest implementation: document `LINGO_SCHEDULER_ENABLED=false` as an env var for multi-worker deployments. A more robust solution involves a startup check via a Redis/Postgres lock: `pg_try_advisory_lock('lingo_scheduler')` — if the lock fails (another process holds it), log WARNING and skip scheduler start.
**Effort:** S → CC: ~15 min
**Priority:** P2
**Depends on:** APScheduler implementation

---

## Notes

Items considered and skipped:
- **Proactive Slack Detection** (📖 emoji reaction): Requires `message.channels` Slack event subscription + in-memory term cache. Skipped — command-based lookup is sufficient and passive monitoring adds noise risk. Revisit if users request it post-launch.
