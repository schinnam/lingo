# Changelog

All notable changes to Lingo are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
