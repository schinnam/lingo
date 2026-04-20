# Lingo — Project Progress

> Update this file as features ship. Statuses: ✅ Done · 🔄 In Progress · ⬜ Not Started

---

## Phase 1 — Core Backend (API + DB)

| Feature | Status | Notes |
|---|---|---|
| Project scaffold (uv, pyproject.toml, dir structure) | ✅ Done | |
| SQLAlchemy models (Term, User, Vote, Token, History, Job) | ✅ Done | |
| Alembic async migration setup | ✅ Done | |
| DB session + async engine | ✅ Done | |
| TermService — CRUD + optimistic locking | ✅ Done | |
| VoteService — dedup + auto status transitions | ✅ Done | |
| FastAPI app skeleton + `/health` | ✅ Done | |
| REST: `POST /api/v1/terms` | ✅ Done | |
| REST: `GET /api/v1/terms` (list + search + filter) | ✅ Done | |
| REST: `GET /api/v1/terms/:id` | ✅ Done | |
| REST: `PUT /api/v1/terms/:id` (versioned update) | ✅ Done | |
| REST: `DELETE /api/v1/terms/:id` | ✅ Done | |
| REST: `POST /api/v1/terms/:id/vote` | ✅ Done | |
| REST: `POST /api/v1/terms/:id/dispute` | ✅ Done | Slack DM deferred to Phase 4 |
| REST: `POST /api/v1/terms/:id/official` | ✅ Done | Editor fast-track |
| REST: `POST /api/v1/terms/:id/confirm` | ✅ Done | Resets staleness |
| REST: `POST /api/v1/terms/:id/claim` | ✅ Done | Claim ownership; editor can override |
| REST: `GET /api/v1/terms/:id/history` | ✅ Done | |
| REST: `POST /api/v1/terms/:id/revert/:history_id` | ✅ Done | Editor only |
| REST: `POST /api/v1/terms/:id/relationships` | ✅ Done | |
| REST: `DELETE /api/v1/terms/:id/relationships/:rel_id` | ✅ Done | |
| REST: `POST /api/v1/terms/:id/promote` | ✅ Done | suggested → pending |
| REST: `POST /api/v1/terms/:id/dismiss` | ✅ Done | Discard suggestion |
| REST: `GET /api/v1/export` | ✅ Done | Markdown export, paginated |
| REST: `GET /api/v1/users` | ✅ Done | Admin only |
| REST: `PATCH /api/v1/users/:id/role` | ✅ Done | Admin only |
| REST: `GET/POST/DELETE /api/v1/tokens` | ✅ Done | API token management |
| REST: `GET /api/v1/admin/stats` | ✅ Done | |
| REST: `GET /api/v1/admin/jobs` | ✅ Done | |
| REST: `POST /api/v1/admin/jobs/:type/run` | ✅ Done | |
| Concurrent vote transaction safety (P1) | ⬜ Not Started | CAS update, concurrency test |

---

## Phase 2 — Auth

| Feature | Status | Notes |
|---|---|---|
| Dev mode auth (`LINGO_DEV_MODE=true`, X-User-Id header) | ✅ Done | X-User-Id only accepted when `settings.dev_mode=True` (security fix) |
| OIDC/SSO middleware (Authlib) | ✅ Done | HS256 JWT; email claim upserts User; RS256/JWKS-URL path in v2 |
| Role enforcement (member / editor / admin) | ✅ Done | `require_role` dep wired to all routes |
| MCP Bearer token auth | ✅ Done | sha256 hash lookup; last_used_at updated on use |
| Token generation (32-byte crypto/rand → base64url) | ✅ Done | |

---

## Phase 3 — MCP Endpoint

| Feature | Status | Notes |
|---|---|---|
| FastMCP app mounted on FastAPI | ✅ Done | Streamable HTTP at `/mcp/`; lifespan wired |
| `get_term(name)` tool | ✅ Done | Case-insensitive name lookup |
| `search_terms(query, status?, limit?)` tool | ✅ Done | Searches name + definition + full_name |
| `list_terms(category?, status?, limit?, offset?)` tool | ✅ Done | Paginated, filterable |
| Bearer token auth on `/mcp` | ✅ Done | MCPBearerAuthMiddleware; sha256 hash lookup |

---

## Phase 4 — Slack Bot

| Feature | Status | Notes |
|---|---|---|
| slack-bolt AsyncApp (Events API) setup | ✅ Done | `lingo/slack/app.py`; Events API via `AsyncSlackRequestHandler` |
| `/lingo define <term>` | ✅ Done | Case-insensitive lookup |
| `/lingo add <term> <definition>` | ✅ Done | Dedup check; anonymous if Slack user unknown |
| `/lingo vote <term>` | ✅ Done | Dedup guard via VoteService |
| `/lingo export` | ✅ Done | `files_upload_v2` Markdown export |
| Dispute DM to term owner | ✅ Done | `send_dispute_dm`; no-op if no owner |
| Promotion notification to source channel | ✅ Done | `send_promotion_notification`; no-op if no source channel |
| Staleness DM to owner (with Confirm/Update buttons) | ✅ Done | Interactive blocks; confirm resets `is_stale` |

---

## Phase 5 — Background Jobs

| Feature | Status | Notes |
|---|---|---|
| APScheduler AsyncIOScheduler setup | ✅ Done | `--workers 1` required; wired into FastAPI lifespan |
| LingoDiscoveryJob — scan Slack history for acronyms | ✅ Done | Regex `\b[A-Z]{2,6}\b`, 90-day window; creates `suggested` terms |
| LingoStalenessJob — weekly stale flag + DM | ✅ Done | `LINGO_STALE_THRESHOLD_DAYS`; DMs owners via `send_staleness_dm` |
| Job progress tracking (progress_json) | ✅ Done | Both jobs write progress_json; failed jobs record error message |

---

## Phase 6 — CLI

| Feature | Status | Notes |
|---|---|---|
| Typer app entry point (`lingo` command) | ✅ Done | `lingo.cli.main:app`; entry point in pyproject.toml |
| `lingo define <term>` | ✅ Done | Case-insensitive; exact match first |
| `lingo add` | ✅ Done | `--full-name`, `--category` options |
| `lingo list` | ✅ Done | `--status`, `--category`, `--limit` filters; rich table |
| `lingo export` | ✅ Done | `--status` filter; `--output` file; prints Markdown |

---

## Phase 7 — Web UI

| Feature | Status | Notes |
|---|---|---|
| React + Vite project setup | ✅ Done | `frontend/`; Vitest + RTL test suite |
| Tailwind CSS + shadcn/ui | ✅ Done | Tailwind v4 via `@tailwindcss/vite` |
| Search bar (reactive, full-width) | ✅ Done | `SearchBar` component; `/` + `Cmd+K` shortcut |
| Status/category filter pills | ✅ Done | `StatusFilter` component with live counts |
| Term list (sorted: Official → Community → Pending) | ✅ Done | `TermRow` table rows; no cards |
| Term detail slide-in panel | ✅ Done | `TermDetail` dialog; relationships, vote/dispute |
| Add term modal | ✅ Done | `AddTermModal` with validation |
| Vote + dispute buttons | ✅ Done | In `TermDetail`; wired to React Query mutations |
| Editor queue (Suggested badge) | ✅ Done | StatusFilter shows live count per status |
| Admin panel (users, roles, jobs) | ⬜ Not Started | Deferred — editor/admin routes TBD |
| Dev mode warning banner | ✅ Done | `DevModeBanner` — reads `<meta name="lingo-dev-mode">` |
| FastAPI static file serving | ✅ Done | SPA fallback route; build → `src/lingo/static/` |

---

## Phase 8 — Deploy

| Feature | Status | Notes |
|---|---|---|
| Dockerfile | ✅ Done | `python:3.12-slim` + uv |
| docker-compose (lingo + postgres) | ✅ Done | |
| Alembic first migration (initial schema) | ✅ Done | `2277c37b0174_initial_schema` — all 7 tables |
| Helm chart (Kubernetes) | ⬜ Not Started | |
| pg_trgm extension migration | ⬜ Not Started | Fuzzy search / "did you mean?" |
| GIN index on `search_vector` | ⬜ Not Started | |

---

## Test Coverage

| Suite | Tests | Status |
|---|---|---|
| Unit: models | 31 | ✅ Passing |
| Unit: TermService | 15 | ✅ Passing |
| Unit: VoteService | 8 | ✅ Passing |
| Unit: API routes | 59 | ✅ Passing |
| Unit: Auth Phase 2 | 14 | ✅ Passing |
| Unit: MCP Phase 3 | 21 | ✅ Passing |
| Unit: Slack Phase 4 | 17 | ✅ Passing |
| Unit: Scheduler Phase 5 | 17 | ✅ Passing |
| Unit: CLI Phase 6 | 16 | ✅ Passing |
| Unit: Web UI Phase 7 (Python) | 7 | ✅ Passing |
| Frontend: Web UI Phase 7 (Vitest) | 48 | ✅ Passing |
| Integration: Postgres (real DB) | 0 | ⬜ Not Started |
| Concurrency: vote race condition | 0 | ⬜ Not Started (P1) |

**Total: 299 / 299 passing (251 pytest + 48 Vitest)**

---

## Backlog (from TODOS.md)

| Item | Priority | Status |
|---|---|---|
| Transactional vote + CAS update | P1 | ⬜ Not Started |
| Export pagination + size cap | P2 | ⬜ Not Started |
| Audit log (AuditEvent table) | P2 | ✅ Done | Integrated into TermService & routes |
| PDF export | P2 | ⬜ Deferred |
