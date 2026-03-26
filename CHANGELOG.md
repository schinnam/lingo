# Changelog

All notable changes to Lingo are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
