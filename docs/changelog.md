# Changelog

All notable changes to Lingo are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.5.5] - 2026-03-27

### Fixed

- **Export endpoint auth (P0):** `GET /api/v1/export` now requires authentication via `CurrentUser` dependency. Previously any unauthenticated caller could paginate the entire glossary with no token required. Fixes #9.

---

## [0.5.4] - 2026-03-26

### Added

- **Integration test infrastructure:** `tests/integration/conftest.py` with real Postgres fixtures — runs Alembic migrations once per session, NullPool engine per test, TRUNCATE for isolation between tests, lifespan override to skip scheduler/MCP, and safe `dependency_overrides` teardown.
- **Integration tests for terms API:** `tests/integration/test_terms.py` covers `POST /api/v1/terms` (201, field validation, auth required) and `GET /api/v1/terms` (200, correct shape, created terms appear).
- **Makefile:** `make test`, `make test-unit`, `make test-integration`, `make db-up`, `make db-down`.

---

## [0.5.3] - 2026-03-26

### Added

- **CORS middleware (P0):** `CORSMiddleware` added with `allow_origins=[settings.app_url]` — scoped to the configured app URL (default: `http://localhost:8000`, overridable via `LINGO_APP_URL`).

---

## [0.5.2] - 2026-03-26

### Fixed

- **Concurrent vote race condition (P1):** Vote insert, count, and status transition now use a CAS `UPDATE ... WHERE status=<expected> AND version=<seen>` — two concurrent requests both hitting the threshold now result in exactly one status transition.
- **API shape mismatch (P0):** `GET /api/v1/terms` now returns `{items, total, offset, limit, counts_by_status}` envelope instead of a bare array.
- **Auth bypass (P0):** `X-User-Id` header now gated behind `settings.dev_mode`; rejected with 401 in production.
- **TermDetail crash (P0):** `term.relationships` guarded with `?? []` — accessing `.length` on the missing field was crashing the detail panel on every open.
- **Form state on cancel (P1):** AddTermModal Cancel button now resets all fields and validation errors before closing.
- **Status filter counts (P1):** Backend returns `counts_by_status` in the list response — per-status counts now reflect all terms across all pages.
- **Alembic downgrade (P1):** `downgrade()` now drops `jobtype`, `jobstatus`, and `relationshiptype` enum types, preventing "type already exists" error on re-upgrade.
- **Double-submit race (P2):** AddTermModal submit button now uses `isPending` from TanStack Query mutation instead of local `submitting` state.

### Added

- `TermsListResponse` Pydantic schema with `items`, `total`, `offset`, `limit`, and `counts_by_status` fields.
- `VoteResponse` TypeScript type in `frontend/src/types/index.ts`.

---

## [0.5.0] - 2026-03-26

### Added

- React + Vite + Tailwind v4 SPA frontend (`frontend/`) compiled into `src/lingo/static/`.
- `SearchBar` with live search and `/` / `Cmd+K` keyboard shortcut.
- `StatusFilter` with filter pills and live per-status counts.
- `TermRow`, `TermDetail`, `AddTermModal`, `DevModeBanner` components.
- TanStack Query hooks (`useTerms`, `useTermDetail`, `useAddTerm`, `useVoteTerm`, `useDisputeTerm`).
- FastAPI SPA fallback route serving `index.html` for all unmatched paths.
- 47 Vitest + React Testing Library tests.

### Fixed

- Alembic migration template (`alembic/script.py.mako`) was missing from the repo.
- Initial database schema migration — creates all 7 tables.

---

## [0.4.0] - 2026-03-26

### Added

- `lingo` CLI entry point via Typer: `define`, `add`, `list`, `export` commands.
- CLI reads `LINGO_APP_URL`, `LINGO_API_TOKEN`, and `LINGO_DEV_USER_ID`.
- 16 new unit tests covering all CLI commands and error paths.

---

## [0.3.0] - 2026-03-26

### Added

- APScheduler `AsyncIOScheduler` wired into FastAPI lifespan.
- `LingoDiscoveryJob` — daily 2 AM Slack acronym scan.
- `LingoStalenessJob` — weekly Monday 3 AM stale-term DMs.
- Both jobs persist a `Job` row with status, `progress_json`, and error.
- 17 new unit tests covering scheduler setup and both jobs.

---

## [0.2.0] - 2026-03-26

### Added

- Slack bot via `slack-bolt` AsyncApp in Socket Mode.
- `/lingo define`, `/lingo add`, `/lingo vote`, `/lingo export` slash commands.
- `send_dispute_dm`, `send_promotion_notification`, `send_staleness_dm` notification helpers.
- `staleness_confirm` and `staleness_update` Block Kit action handlers.
- 17 new unit tests covering all handlers.

### Changed

- `handle_lingo_add` now requires a linked Lingo account; anonymous term creation via Slack is rejected.

---

## [0.1.0] - 2026-03-01

### Added

- Initial project scaffold (FastAPI, SQLAlchemy async, Alembic, uv).
- Full REST API for terms, votes, disputes, history, relationships, export.
- OIDC/SSO auth middleware (HS256 JWT) and MCP Bearer token auth.
- FastMCP app mounted at `/mcp` with `get_term`, `search_terms`, `list_terms` tools.
- Dev mode auth (`LINGO_DEV_MODE=true`, `X-User-Id` header).
- Docker + docker-compose setup.
