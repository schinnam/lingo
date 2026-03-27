# Lingo Architecture

Lingo is a single Python service (FastAPI + asyncpg + Postgres) with three client surfaces: a web SPA, a Slack bot, and a CLI. A FastMCP endpoint at `/mcp` exposes the glossary to AI agents.

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
│  └────────────────────────────────────────────────────┘  │
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

## Directory structure

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
│       └── admin.py     # /api/v1/admin
├── auth/
│   └── oidc.py          # OIDC/JWT middleware
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
│   └── vote_service.py  # Vote dedup, status promotion
├── models/              # SQLAlchemy ORM models
│   ├── term.py
│   ├── user.py
│   ├── vote.py
│   ├── token.py
│   ├── job.py
│   ├── term_history.py
│   └── term_relationship.py
└── db/
    └── session.py       # AsyncSession factory (asyncpg driver)

frontend/                # React + Vite SPA (compiled → src/lingo/static/)
├── src/
│   ├── api/terms.ts     # Axios API client
│   ├── hooks/useTerms.ts# TanStack Query hooks
│   ├── components/      # SearchBar, StatusFilter, TermRow, TermDetail, AddTermModal, DevModeBanner
│   └── types/index.ts   # TypeScript types
└── test/                # Vitest + React Testing Library

alembic/                 # Database migrations
tests/                   # pytest (async, aiosqlite in-memory DB)
```

---

## Data model

Seven tables. The core is `terms` — everything else supports it.

```
users          — accounts; role: viewer | editor | admin
terms          — the glossary; status: suggested | pending | community | official
votes          — one vote per (user, term); drives status transitions
term_history   — append-only log of every term edit
term_relationships — synonym / antonym / related links between terms
tokens         — API bearer tokens for programmatic access
jobs           — scheduler job run log (status, progress_json, error)
```

### Term status lifecycle

```
suggested → pending → community → official
               ↑           ↑
        (any user vote)  (vote count ≥ community_threshold)
                                       ↓
                              official (editor action,
                              vote count ≥ official_threshold)
```

Votes are tallied per term. `VoteService` checks both thresholds on every vote and triggers the transition automatically. Editors can also manually `promote` or `mark_official` via the API.

---

## Auth

Three modes, evaluated in order by the `CurrentUser` dependency in `api/deps.py`:

1. **JWT Bearer** — HS256 token signed with `LINGO_SECRET_KEY`. Standard production path.
2. **OIDC** — if `LINGO_OIDC_DISCOVERY_URL` is set, tokens are validated against the OIDC provider.
3. **Dev mode** — `LINGO_DEV_MODE=true` only. `X-User-Id: <uuid>` header accepted. Rejected with 401 in production.

The MCP endpoint has its own auth middleware (`MCPBearerAuthMiddleware`) using `LINGO_MCP_BEARER_TOKEN`. It wraps the FastMCP ASGI app and is mounted at `/mcp`.

---

## Scheduler

APScheduler's `AsyncIOScheduler` starts in the FastAPI lifespan and shares the same event loop. Two jobs:

- **DiscoveryJob** — runs daily at 2 AM. Scans public Slack channels over a 90-day window, extracts uppercase acronyms (`[A-Z]{2,6}`), and creates `suggested` terms for any not already in the glossary.
- **StalenessJob** — runs weekly Monday at 3 AM. Finds terms where `last_confirmed_at` is older than `LINGO_STALE_THRESHOLD_DAYS` (default 180), sets `is_stale=true`, and DMs their owners via Slack Block Kit.

Both jobs write a `Job` row with status, a `progress_json` blob, and any error message.

The scheduler requires `--workers 1` on uvicorn. Multiple workers would each start their own scheduler and run jobs multiple times.

---

## MCP server

FastMCP is mounted as a sub-ASGI app at `/mcp`. Three read-only tools:

- `get_term(name)` — exact case-insensitive lookup
- `search_terms(query, status?, limit?)` — full-text search across name, definition, full_name
- `list_terms(category?, status?, limit?, offset?)` — paginated list

These are read-only by design. Write operations (adding terms, voting) go through the REST API or Slack bot, where the user identity and authorization flow are well-defined.

---

## Frontend

A React + Vite SPA compiled into `src/lingo/static/`. FastAPI mounts `/assets` as static files and falls back all unmatched routes to `index.html` for React Router.

When `LINGO_DEV_MODE=true`, FastAPI injects `<meta name="lingo-dev-mode" content="true">` into the served HTML. The `DevModeBanner` component reads this at runtime to show a dev mode indicator without a separate API call.

Components: `SearchBar`, `StatusFilter`, `TermRow`, `TermDetail`, `AddTermModal`, `DevModeBanner`.

State is managed with TanStack Query (`useTerms`, `useTermDetail`, `useAddTerm`, `useVoteTerm`, `useDisputeTerm`).

---

## Slack bot

`slack-bolt` `AsyncApp` running in Socket Mode. No public URL or webhook required — the bot connects outbound to Slack's API.

Slash command handlers: `define`, `add`, `vote`, `export`.
Notification helpers: `send_dispute_dm`, `send_promotion_notification`, `send_staleness_dm`.
Interactive action handlers: `staleness_confirm`, `staleness_update` (Block Kit callbacks).

`handle_lingo_add` requires a linked Lingo account (anonymous Slack adds are rejected). This prevents orphaned terms with no responsible owner.

---

## Key design decisions

**Single process, async throughout.** FastAPI + asyncpg + APScheduler all run on the same asyncio event loop. This keeps the deployment simple (no separate worker process, no Redis) at the cost of requiring `--workers 1`.

**Dev mode is a hard gate.** `X-User-Id` header auth is rejected with 401 unless `LINGO_DEV_MODE=true`. This is enforced in the `CurrentUser` dependency, not just documented. The test for it lives in `tests/test_terms.py::test_x_user_id_rejected_when_dev_mode_off`.

**Term status is append-only via history.** Every edit creates a `TermHistory` row. The `revert` endpoint restores a previous version by creating a new edit, not by modifying history.

**Optimistic concurrency on updates.** `PUT /api/v1/terms/{id}` requires a `version` field matching the current row version. A mismatch returns 409. This prevents silent overwrites when two editors edit the same term concurrently.

**MCP is read-only.** Write access via AI agents would bypass the user identity and vote-based governance model. Keeping MCP read-only is intentional.
