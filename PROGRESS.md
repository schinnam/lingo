# Lingo — Project Progress

> Update this file as features ship. Statuses: ✅ Done · 🔄 In Progress · ⬜ Not Started

---

## Phase 1 — Core Backend (API + DB)

| Feature | Status | Notes |
|---|---|---|
| Project scaffold (uv, pyproject.toml, dir structure) | ✅ Done | |
| SQLAlchemy models (Term, User, Vote, Token, History, Job) | ✅ Done | |
| Alembic async migration setup | ✅ Done | Needs first migration generated |
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
| REST: `POST /api/v1/terms/:id/dispute` | ⬜ Not Started | Notifies owner via Slack DM |
| REST: `POST /api/v1/terms/:id/official` | ⬜ Not Started | Editor fast-track |
| REST: `POST /api/v1/terms/:id/confirm` | ⬜ Not Started | Resets staleness |
| REST: `POST /api/v1/terms/:id/claim` | ⬜ Not Started | Claim ownership |
| REST: `GET /api/v1/terms/:id/history` | ⬜ Not Started | |
| REST: `POST /api/v1/terms/:id/revert/:history_id` | ⬜ Not Started | Editor only |
| REST: `POST /api/v1/terms/:id/relationships` | ⬜ Not Started | |
| REST: `DELETE /api/v1/terms/:id/relationships/:rel_id` | ⬜ Not Started | |
| REST: `POST /api/v1/terms/:id/promote` | ⬜ Not Started | suggested → pending |
| REST: `POST /api/v1/terms/:id/dismiss` | ⬜ Not Started | Discard suggestion |
| REST: `GET /api/v1/export` | ⬜ Not Started | Markdown export, paginated |
| REST: `GET /api/v1/users` | ⬜ Not Started | Admin only |
| REST: `PATCH /api/v1/users/:id/role` | ⬜ Not Started | Admin only |
| REST: `GET/POST/DELETE /api/v1/tokens` | ⬜ Not Started | API token management |
| REST: `GET /api/v1/admin/stats` | ⬜ Not Started | |
| REST: `GET /api/v1/admin/jobs` | ⬜ Not Started | |
| REST: `POST /api/v1/admin/jobs/:type/run` | ⬜ Not Started | |
| Concurrent vote transaction safety (P1) | ⬜ Not Started | CAS update, concurrency test |

---

## Phase 2 — Auth

| Feature | Status | Notes |
|---|---|---|
| Dev mode auth (`LINGO_DEV_MODE=true`, X-User-Id header) | ✅ Done | Warning banner needed in UI |
| OIDC/SSO middleware (Authlib) | ⬜ Not Started | Google Workspace, Okta, generic OIDC |
| Role enforcement (member / editor / admin) | ⬜ Not Started | Middleware + per-route checks |
| MCP Bearer token auth | ⬜ Not Started | sha256 hash lookup |
| Token generation (32-byte crypto/rand → base64url) | ⬜ Not Started | |

---

## Phase 3 — MCP Endpoint

| Feature | Status | Notes |
|---|---|---|
| FastMCP app mounted on FastAPI | ⬜ Not Started | Streamable HTTP transport |
| `get_term(name)` tool | ⬜ Not Started | |
| `search_terms(query, status?, limit?)` tool | ⬜ Not Started | |
| `list_terms(category?, status?, limit?, offset?)` tool | ⬜ Not Started | |
| Bearer token auth on `/mcp` | ⬜ Not Started | |

---

## Phase 4 — Slack Bot

| Feature | Status | Notes |
|---|---|---|
| slack-bolt AsyncApp (Socket Mode) setup | ⬜ Not Started | |
| `/lingo define <term>` | ⬜ Not Started | |
| `/lingo add <term> <definition>` | ⬜ Not Started | |
| `/lingo vote <term>` | ⬜ Not Started | |
| `/lingo export` | ⬜ Not Started | File upload |
| Dispute DM to term owner | ⬜ Not Started | |
| Promotion notification to source channel | ⬜ Not Started | |
| Staleness DM to owner (with Confirm/Update buttons) | ⬜ Not Started | |

---

## Phase 5 — Background Jobs

| Feature | Status | Notes |
|---|---|---|
| APScheduler AsyncIOScheduler setup | ⬜ Not Started | `--workers 1` required |
| LingoDiscoveryJob — scan Slack history for acronyms | ⬜ Not Started | Regex `\b[A-Z]{2,6}\b`, 90-day window |
| LingoStalenessJob — weekly stale flag + DM | ⬜ Not Started | `LINGO_STALE_THRESHOLD_DAYS` |
| Job progress tracking (progress_json) | ⬜ Not Started | Resumable |

---

## Phase 6 — CLI

| Feature | Status | Notes |
|---|---|---|
| Typer app entry point (`lingo` command) | ⬜ Not Started | |
| `lingo define <term>` | ⬜ Not Started | |
| `lingo add` | ⬜ Not Started | |
| `lingo list` | ⬜ Not Started | |
| `lingo export` | ⬜ Not Started | |

---

## Phase 7 — Web UI

| Feature | Status | Notes |
|---|---|---|
| React + Vite project setup | ⬜ Not Started | Compiled to `src/lingo/static/` |
| Tailwind CSS + shadcn/ui | ⬜ Not Started | |
| Search bar (reactive, full-width) | ⬜ Not Started | |
| Status/category filter pills | ⬜ Not Started | |
| Term list (sorted: Official → Community → Pending) | ⬜ Not Started | |
| Term detail slide-in panel | ⬜ Not Started | |
| Add term modal | ⬜ Not Started | |
| Vote + dispute buttons | ⬜ Not Started | |
| Editor queue (Suggested badge) | ⬜ Not Started | |
| Admin panel (users, roles, jobs) | ⬜ Not Started | |
| Dev mode warning banner | ⬜ Not Started | |
| FastAPI static file serving | ⬜ Not Started | |

---

## Phase 8 — Deploy

| Feature | Status | Notes |
|---|---|---|
| Dockerfile | ✅ Done | `python:3.12-slim` + uv |
| docker-compose (lingo + postgres) | ✅ Done | |
| Alembic first migration (initial schema) | ⬜ Not Started | `uv run alembic revision --autogenerate` |
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
| Unit: API routes | 14 | ✅ Passing |
| Integration: Postgres (real DB) | 0 | ⬜ Not Started |
| Concurrency: vote race condition | 0 | ⬜ Not Started (P1) |

**Total: 68 / 68 passing**

---

## Backlog (from TODOS.md)

| Item | Priority | Status |
|---|---|---|
| Transactional vote + CAS update | P1 | ⬜ Not Started |
| Export pagination + size cap | P2 | ⬜ Not Started |
| Audit log (AuditEvent table) | P2 | ⬜ Not Started |
| PDF export | P2 | ⬜ Deferred |
