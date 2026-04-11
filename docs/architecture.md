# Architecture

Lingo is a single Python service (FastAPI + asyncpg + PostgreSQL) with three client surfaces: a web SPA, a Slack bot, and a CLI. A FastMCP endpoint at `/mcp` exposes the glossary to AI agents.

---

## Component overview

```
┌─────────────────────────────────────────────────────────┐
│                     Lingo Server (FastAPI)               │
│                                                         │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────┐  │
│  │  REST API       │  │  FastMCP /mcp  │  │ Static   │  │
│  │  /api/v1/*     │  │  (bearer auth) │  │ SPA      │  │
│  └───────┬────────┘  └───────┬────────┘  └──────────┘  │
│          │                   │                           │
│  ┌───────▼───────────────────▼───────────────────────┐  │
│  │              Services (TermService, VoteService)   │  │
│  └───────────────────────┬───────────────────────────┘  │
│                          │                               │
│  ┌───────────────────────▼───────────────────────────┐  │
│  │       SQLAlchemy async models + Alembic            │  │
│  └───────────────────────┬───────────────────────────┘  │
│                          │                               │
│  ┌───────────────────────▼───────────────────────────┐  │
│  │                  PostgreSQL                        │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌────────────────────────────────────────────────────┐  │
│  │   APScheduler (in-process, AsyncIOScheduler)       │  │
│  │   DiscoveryJob (daily 2am) | StalenessJob (Mon 3am)│  │
│  └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘

       ▲                    ▲                    ▲
  Slack Bot             CLI (httpx)         Web Browser
  (Socket Mode)         LINGO_APP_URL       React SPA
```

---

## Source structure

```
src/lingo/
├── main.py              # FastAPI app, lifespan, route wiring
├── config.py            # Settings (pydantic-settings, LINGO_ prefix)
├── api/
│   ├── deps.py          # FastAPI dependencies: CurrentUser, SessionDep, EditorUser
│   ├── schemas.py       # Pydantic request/response schemas
│   └── routes/
│       ├── terms.py     # /api/v1/terms — all term CRUD + actions
│       ├── export.py    # /api/v1/export
│       ├── users.py     # /api/v1/users
│       ├── tokens.py    # /api/v1/tokens
│       ├── admin.py     # /api/v1/admin
│       └── features.py  # /api/v1/features
├── auth/
│   └── oidc.py          # Slack OAuth + JWT middleware
├── mcp/
│   ├── app.py           # FastMCP tools: get_term, search_terms, list_terms
│   └── auth.py          # MCPBearerAuthMiddleware
├── slack/
│   └── app.py           # Slack-bolt AsyncApp, command handlers, DM helpers
├── cli/
│   └── main.py          # Typer CLI: define, add, list, export
├── scheduler/
│   ├── setup.py         # APScheduler wiring
│   └── jobs/
│       ├── discovery.py # Daily Slack acronym scan
│       └── staleness.py # Weekly stale-term DMs
├── services/
│   ├── term_service.py  # Business logic: create, update, vote thresholds, history
│   └── vote_service.py  # Vote dedup, status promotion (CAS-based)
├── models/              # SQLAlchemy ORM models (7 tables)
└── db/
    └── session.py       # AsyncSession factory (asyncpg driver)

frontend/                # React + Vite SPA (compiled → src/lingo/static/)
alembic/                 # Database migrations
tests/
├── unit/                # pytest (async, aiosqlite in-memory DB — no Docker)
└── integration/         # pytest (async, real Postgres — requires Docker)
```

---

## Data model

Seven tables. The core is `terms` — everything else supports it.

| Table | Purpose |
|---|---|
| `users` | Accounts; role: `viewer` \| `editor` \| `admin` |
| `terms` | The glossary; status: `suggested` \| `pending` \| `community` \| `official` |
| `votes` | One vote per `(user, term)`; drives status transitions |
| `term_history` | Append-only log of every term edit |
| `term_relationships` | Synonym / antonym / related links between terms |
| `tokens` | API bearer tokens for programmatic access |
| `jobs` | Scheduler job run log (status, `progress_json`, error) |

### Term status lifecycle

```
suggested → pending → community → official
               ↑           ↑
        (any user vote)  (vote count ≥ community_threshold)
                                       ↓
                              official (editor action,
                              vote count ≥ official_threshold)
```

`VoteService` checks both thresholds on every vote and triggers the transition automatically. Editors can also manually `promote` or `mark_official` via the API.

---

## Authentication

Three modes, evaluated in order by the `CurrentUser` dependency:

1. **Slack OAuth** — the web UI uses Sign in with Slack (`openid`, `email`, `profile` scopes). The callback at `/auth/slack/callback` exchanges the code for tokens, creates or updates the user record, and issues a session JWT signed with `LINGO_SECRET_KEY`. Requires `LINGO_SLACK_CLIENT_ID` and `LINGO_SLACK_CLIENT_SECRET`.
2. **JWT Bearer** — HS256 token signed with `LINGO_SECRET_KEY`. Used by the CLI, MCP, and direct API clients after obtaining a token via Slack OAuth or an admin-issued API token.
3. **Dev mode** — `LINGO_DEV_MODE=true` only. Visit `/auth/dev/login?email=you@example.com` to get a session without Slack. `X-User-Id: <uuid>` header is also accepted for CLI use in dev. Both are rejected with `401` in production.

The MCP endpoint has its own auth middleware (`MCPBearerAuthMiddleware`) validating against `LINGO_MCP_BEARER_TOKEN`.

CORS is restricted to `LINGO_APP_URL` (default: `http://localhost:8000`).

---

## Scheduler

`APScheduler`'s `AsyncIOScheduler` starts in the FastAPI lifespan and shares the same event loop:

- **DiscoveryJob** — runs daily at 2 AM. Scans public Slack channels over a 90-day window, extracts uppercase acronyms (`[A-Z]{2,6}`), and creates `suggested` terms for any not already in the glossary.
- **StalenessJob** — runs weekly Monday at 3 AM. Finds terms where `last_confirmed_at` is older than `LINGO_STALE_THRESHOLD_DAYS`, sets `is_stale=true`, and DMs owners via Slack Block Kit.

Both jobs write a `Job` row with status, a `progress_json` blob, and any error message.

**`--workers 1` is required.** Multiple workers would each start their own scheduler and run jobs multiple times.

---

## MCP server

FastMCP is mounted as a sub-ASGI app at `/mcp`. Three read-only tools:

- `get_term(name)` — exact case-insensitive lookup
- `search_terms(query, status?, limit?)` — full-text search
- `list_terms(category?, status?, limit?, offset?)` — paginated list

Read-only by design. Write operations go through the REST API or Slack bot where user identity and governance are well-defined.

---

## Key design decisions

**Single process, async throughout.** FastAPI + asyncpg + APScheduler share one asyncio event loop. Keeps deployment simple at the cost of requiring `--workers 1`.

**Dev mode is a hard gate.** `X-User-Id` header auth is rejected with `401` unless `LINGO_DEV_MODE=true`. Enforced in the `CurrentUser` dependency, not just documented.

**Term status is append-only via history.** Every edit creates a `TermHistory` row. The `revert` endpoint restores a previous version by creating a new edit, not by modifying history.

**Optimistic concurrency on updates.** `PUT /api/v1/terms/{id}` requires a `version` field matching the current row. A mismatch returns `409`. This prevents silent overwrites when two editors update the same term concurrently.

**CAS on vote status transitions.** `VoteService.vote()` uses a compare-and-swap `UPDATE terms SET status=?, version=version+1 WHERE id=? AND status=? AND version=?`. Two concurrent votes both hitting the threshold race; exactly one wins (`rowcount=1`) and fires the transition. Both votes still succeed — the transition fires once.

**MCP is read-only.** Write access via AI agents would bypass the community vote-based governance model. Keeping MCP read-only is intentional.

**API-first design.** The REST API is the source of truth. The Slack bot, web UI, and CLI are thin clients over it.
