# Changelog

All notable changes to Lingo are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.5.3] - 2026-03-26

### Added
- **CORS middleware (P0):** `CORSMiddleware` added with `allow_origins=[settings.app_url]` — scoped to the configured app URL (default: `http://localhost:8000`, overridable via `LINGO_APP_URL`). Prevents `allow_origins=["*"]` footgun when frontend integration is added.

## [0.5.2] - 2026-03-26

### Fixed
- **Concurrent vote race condition (P1):** Vote insert, count, and status transition now use a CAS `UPDATE ... WHERE status=<expected> AND version=<seen>` — two concurrent requests both hitting the threshold now result in exactly one status transition instead of both firing
- **Concurrency test:** Added `test_vote_concurrent_at_threshold` — spawns two async sessions via `asyncio.gather` and asserts exactly one `to_community` transition fires

## [0.5.1] - 2026-03-26

### Fixed
- **API shape mismatch (P0):** `GET /api/v1/terms` now returns `{ items, total, offset, limit, counts_by_status }` envelope instead of a bare array — term list was always empty in production
- **Auth bypass (P0):** `X-User-Id` header now gated behind `settings.dev_mode`; rejected with 401 in production, preventing any caller from impersonating users via UUID
- **TermDetail crash (P0):** `term.relationships` guarded with `?? []` — accessing `.length` on the missing field was crashing the detail panel on every open
- **Form state on cancel (P1):** AddTermModal Cancel button now resets all fields and validation errors before closing
- **Status filter counts (P1):** Backend returns `counts_by_status` in the list response — per-status counts now reflect all terms across all pages, not just the current page
- **Alembic downgrade (P1):** `downgrade()` now drops `jobtype`, `jobstatus`, and `relationshiptype` enum types, preventing "type already exists" error on re-upgrade
- **Double-submit race (P2):** AddTermModal submit button now uses `isPending` from TanStack Query mutation (synchronous) instead of local `submitting` state, preventing duplicate POST on fast double-click
- **voteTerm type lie (P2):** `voteTerm` in `terms.ts` now correctly typed as `Promise<VoteResponse>` matching the backend's actual `{ vote_count, transition }` response
- **counts_by_status key safety:** Status keys in `counts_by_status` explicitly cast to `str` to guard against asyncpg returning non-string enum labels

### Added
- `TermsListResponse` Pydantic schema with `items`, `total`, `offset`, `limit`, and `counts_by_status` fields
- `VoteResponse` TypeScript type in `frontend/src/types/index.ts`
- Test: `test_list_terms_counts_by_status` — verifies `counts_by_status` is present and reflects all terms
- Test: `test_x_user_id_rejected_when_dev_mode_off` — regression guard for the auth bypass security fix

## [0.5.0] - 2026-03-26

### Added
- React + Vite + Tailwind v4 SPA frontend (`frontend/`) compiled into `src/lingo/static/`
- `SearchBar` component with live search; keyboard shortcut `/` and `Cmd+K` focus the search bar
- `StatusFilter` component with filter pills (All / Official / Community / Pending / Suggested) and live per-status counts
- `TermRow` table rows for the term list; sorted by status (Official first)
- `TermDetail` slide-in panel with relationships, vote count, and vote / dispute action buttons
- `AddTermModal` with name, full name, definition, category fields; client-side validation (name and definition required)
- `DevModeBanner` component — reads `<meta name="lingo-dev-mode">` injected by FastAPI when `LINGO_DEV_MODE=true`
- React Query hooks (`useTerms`, `useTermDetail`, `useAddTerm`, `useVoteTerm`, `useDisputeTerm`) in `frontend/src/hooks/useTerms.ts`
- Axios-based API client in `frontend/src/api/terms.ts`
- FastAPI SPA fallback route: `/{full_path:path}` serves `index.html` for all unmatched paths so React Router works correctly
- Dev mode meta tag injection: `<meta name="lingo-dev-mode">` inserted into `index.html` at request time when `LINGO_DEV_MODE=true`
- 47 Vitest + React Testing Library tests covering all 7 components and the API layer
- 7 pytest tests covering SPA static file serving, health endpoint, and API route priority

### Fixed
- API error state: when backend is unavailable, the UI now shows "Could not load terms. Check your connection and try again." instead of the misleading "No terms found."
- Alembic migration template (`alembic/script.py.mako`) was missing from the repo, preventing `alembic revision` from running; added the standard template
- Initial database schema migration (`2277c37b0174_initial_schema`) — creates all 7 tables: `users`, `terms`, `tokens`, `jobs`, `term_history`, `term_relationships`, `votes`

### Changed
- `.gitignore` now excludes `.gstack/` directory (QA reports, browser session artifacts)

## [0.4.0] - 2026-03-26

### Added
- `lingo` CLI entry point (`src/lingo/cli/main.py`) via Typer, pip-installable as `lingo` command
- `lingo define <term>` — looks up a term by name via the REST API; exact case-insensitive match first, then first result; rich-formatted output with name, full name, definition, status, vote count, and category
- `lingo add <term> <definition>` — adds a new term to the glossary; `--full-name`/`-f` and `--category`/`-c` options
- `lingo list` — displays glossary terms in a rich table; supports `--status`/`-s`, `--category`/`-c`, and `--limit`/`-n` filters
- `lingo export` — exports glossary as Markdown to stdout or `--output`/`-o` file; `--status`/`-s` filter (default: official)
- CLI reads `LINGO_APP_URL` (default `http://localhost:8000`), `LINGO_API_TOKEN` (Bearer auth), and `LINGO_DEV_USER_ID` (dev mode X-User-Id header)
- 16 new unit tests covering all commands, options, error paths, and file export (198 total, all passing)

## [0.3.0] - 2026-03-26

### Added
- APScheduler `AsyncIOScheduler` wired into the FastAPI lifespan (`src/lingo/scheduler/setup.py`); starts on boot, shuts down gracefully (requires `--workers 1`)
- `LingoDiscoveryJob` — daily 2 AM job that scans all public Slack channels over a 90-day window, extracts acronyms matching `\b[A-Z]{2,6}\b`, and creates `suggested` terms for any not already in the glossary (`src/lingo/scheduler/jobs/discovery.py`)
- `LingoStalenessJob` — weekly Monday 3 AM job that flags terms whose `last_confirmed_at` exceeds `LINGO_STALE_THRESHOLD_DAYS` and DMs their owners via the existing `send_staleness_dm` helper (`src/lingo/scheduler/jobs/staleness.py`)
- Both jobs persist a `Job` row with `status`, `progress_json` (channels scanned, terms found / terms flagged, DMs sent), and `error` on failure
- 17 new unit tests covering scheduler setup, discovery job, and staleness job (182 total, all passing)

## [0.2.0] - 2026-03-26

### Added
- Slack bot via `slack-bolt` AsyncApp in Socket Mode (`src/lingo/slack/app.py`)
- `/lingo define <term>` — case-insensitive glossary lookup from Slack
- `/lingo add <term> -- <definition>` — add a pending term from Slack (requires linked Lingo account)
- `/lingo vote <term>` — cast a vote for a term from Slack (dedup-guarded via VoteService)
- `/lingo export` — upload full glossary as a Markdown file to the current channel (capped at 1,000 terms)
- `send_dispute_dm` — DMs the term owner when a dispute is filed (no-op if no owner)
- `send_promotion_notification` — posts to the source channel when a term is promoted (no-op if no source channel)
- `send_staleness_dm` — sends an interactive Block Kit DM with Confirm/Update buttons when a term becomes stale
- `staleness_confirm` and `staleness_update` interactive action handlers
- `LINGO_SLACK_SIGNING_SECRET` config setting for request signature validation
- 17 new unit tests covering all handlers and notification helpers (165 total, all passing)

### Changed
- `handle_lingo_add` now requires a linked Lingo account; anonymous term creation via Slack is rejected
- Export query capped at 1,000 terms (`_EXPORT_LIMIT`) to prevent memory exhaustion
- Action handlers validate `term_id` is a valid UUID before querying the database

## [0.1.0] - 2026-03-01

### Added
- Initial project scaffold (FastAPI, SQLAlchemy async, Alembic, uv)
- Full REST API for terms, votes, disputes, history, relationships, export
- OIDC/SSO auth middleware (HS256 JWT) and MCP Bearer token auth
- FastMCP app mounted at `/mcp` with `get_term`, `search_terms`, `list_terms` tools
- Dev mode auth (`LINGO_DEV_MODE=true`, `X-User-Id` header)
- Docker + docker-compose setup
