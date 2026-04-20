# Lingo

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Self-hosted company glossary. Slack, CLI, web UI, and AI agents — all from one service.

Teams grow and accumulate jargon fast. Lingo is where you put it. Add a term from Slack, vote it up, and AI agents can look it up via MCP. Stale terms get a nudge. The whole thing runs on Postgres.

---

## What it does

- **Web UI** — searchable term browser with status filters, vote / dispute actions, and a slide-in detail panel
- **Slack bot** — `/lingo define`, `/lingo add`, `/lingo vote`, `/lingo export` commands
- **CLI** — `lingo define`, `lingo add`, `lingo list`, `lingo export`
- **REST API** — full CRUD at `/api/v1/terms` with Slack OAuth + JWT auth
- **MCP server** — `get_term`, `search_terms`, `list_terms` tools for Claude and other MCP-aware agents
- **Auto-discovery** — daily job scans Slack for unknown acronyms and creates `suggested` terms
- **Staleness tracking** — weekly job DMs term owners when a term hasn't been confirmed in 180 days

Terms flow through statuses: `suggested` → `pending` → `community` → `official`. User-added terms start at `pending`; `suggested` is reserved for auto-discovered terms.

---

## Quickstart (Docker)

The fastest path: PostgreSQL + Lingo server with one command.

```bash
git clone https://github.com/schinnam/lingo
cd lingo
# 1. Edit docker-compose.yml or create docker-compose.override.yml with your tokens
# 2. Build and start
docker compose up --build
```

The server starts at `http://localhost:8000`. Dev mode is on by default in the compose file — visit `http://localhost:8000/auth/dev/login?email=you@example.com` to log in without Slack.

Open `http://localhost:8000` to see the web UI.

---

## Local development

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (`brew install uv` on macOS)
- PostgreSQL 14+ (or use Docker for just the database)

### 1. Start a database

```bash
docker compose up postgres -d
```

Or use any Postgres instance and set `LINGO_DATABASE_URL` accordingly.

### 2. Install dependencies and run migrations

```bash
uv sync
LINGO_DEV_MODE=true uv run alembic upgrade head
```

### 3. Start the server

```bash
LINGO_DEV_MODE=true uv run uvicorn lingo.main:app --reload
```

The server is at `http://localhost:8000`. Interactive API docs at `http://localhost:8000/docs`.

### 4. Build the frontend (optional)

The repo ships a pre-built frontend. To rebuild after making UI changes:

```bash
cd frontend
npm install
npm run build
```

The build output goes to `src/lingo/static/` and is served by the FastAPI app.

---

## Configuration

All settings use the `LINGO_` prefix. Set them via environment variables or a `.env` file.

| Variable | Default | Description |
|---|---|---|
| `LINGO_DATABASE_URL` | `postgresql+asyncpg://lingo:lingo@localhost:5432/lingo` | Postgres connection string |
| `LINGO_DEV_MODE` | `false` | Enables `X-User-Id` header auth (dev only — never in production) |
| `LINGO_SECRET_KEY` | `change-me-in-production` | JWT signing key |
| `LINGO_SLACK_CLIENT_ID` | `""` | Slack app Client ID (required for web UI login) |
| `LINGO_SLACK_CLIENT_SECRET` | `""` | Slack app Client Secret |
| `LINGO_SLACK_BOT_TOKEN` | `""` | Slack bot token (Socket Mode) |
| `LINGO_SLACK_APP_TOKEN` | `""` | Slack app-level token |
| `LINGO_SLACK_SIGNING_SECRET` | `""` | Slack signing secret |
| `LINGO_MCP_BEARER_TOKEN` | `""` | Bearer token for MCP endpoint |
| `LINGO_COMMUNITY_THRESHOLD` | `3` | Votes needed to promote `pending` → `community` |
| `LINGO_OFFICIAL_THRESHOLD` | `10` | Votes needed for editor to mark `community` → `official` |
| `LINGO_STALE_THRESHOLD_DAYS` | `180` | Days since last confirmation before a term is flagged stale |
| `LINGO_APP_URL` | `http://localhost:8000` | Public base URL (used by Slack notifications) |

> **Note:** The web UI requires Slack for login. Users without Slack can still use the CLI and MCP endpoint via API tokens.

### Slack App Setup

To enable web UI login, create a Slack app and configure OAuth:

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps) and create or open your Slack app
2. Under **OAuth & Permissions**, add a redirect URI: `https://<your-domain>/auth/slack/callback`
3. Under **OAuth & Permissions → OpenID Connect Scopes**, add: `openid`, `email`, `profile`
4. Copy **Client ID** and **Client Secret** from **Basic Information** and set `LINGO_SLACK_CLIENT_ID` and `LINGO_SLACK_CLIENT_SECRET`

Bot scopes (`commands`, `chat:write`) and Sign in with Slack (`openid`) are separate flows that coexist in the same Slack app.

---

## CLI

Install the `lingo` command:

```bash
uv pip install -e .
```

> **Note:** `uv pip install -e .` installs into the project virtualenv, so `lingo` may not be on your shell `PATH`. Use `uv run lingo` from the repo directory, or install as a global tool with `uv tool install .` to get a `lingo` command anywhere.

Point it at your server:

```bash
export LINGO_APP_URL=http://localhost:8000
export LINGO_API_TOKEN=your-token   # or LINGO_DEV_USER_ID=<uuid> in dev mode
```

### Commands

```bash
# Look up a term
uv run lingo define API

# Add a term (dev mode: set LINGO_DEV_USER_ID to any valid user UUID)
LINGO_DEV_USER_ID=<uuid> uv run lingo add "SLA" "Service Level Agreement" --full-name "Service Level Agreement" --category ops

# List terms
uv run lingo list
uv run lingo list --status official
uv run lingo list --category tech --limit 20

# Export as Markdown
# Default exports 'official' terms only — use --status to export others
uv run lingo export --status pending
uv run lingo export --status community --output glossary.md
```

---

## Slack bot

Set `LINGO_SLACK_BOT_TOKEN`, `LINGO_SLACK_APP_TOKEN`, and `LINGO_SLACK_SIGNING_SECRET`, then start the server. The bot uses Socket Mode — no public URL needed.

```
/lingo define API
/lingo add BART -- Bay Area Rapid Transit
/lingo vote BART
/lingo export
```

Terms added via Slack require a linked Lingo account. The bot DMs term owners when their terms are disputed or go stale.

---

## MCP (AI agents)

The MCP server is at `/mcp`. It requires a bearer token (`LINGO_MCP_BEARER_TOKEN`).

To connect Claude Desktop, add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "lingo": {
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer your-token"
      }
    }
  }
}
```

Available tools: `get_term`, `search_terms`, `list_terms`.

---

## Running tests

Unit tests (no Docker required):

```bash
uv run pytest tests/unit/
# or
make test-unit
```

Integration tests (requires Docker — hits a real Postgres container):

```bash
make test-integration   # starts postgres, creates lingo_test DB, runs migrations, runs tests
```

All tests:

```bash
make test
```

Frontend tests:

```bash
cd frontend
npm test
```

---

## Production deployment

Use the Docker image. Set `LINGO_DEV_MODE=false` and provide real values for `LINGO_SECRET_KEY`, `LINGO_SLACK_CLIENT_ID`, and `LINGO_SLACK_CLIENT_SECRET`. The scheduler requires `--workers 1` (APScheduler runs in-process).

```bash
docker build -t lingo .
docker run -p 8000:8000 \
  -e LINGO_DATABASE_URL=postgresql+asyncpg://... \
  -e LINGO_SECRET_KEY=your-secret \
  -e LINGO_DEV_MODE=false \
  lingo
```

Run migrations before the first boot:

```bash
docker run --rm -e LINGO_DATABASE_URL=... lingo uv run alembic upgrade head
```

---

## API reference

Interactive docs: `http://localhost:8000/docs`

Key endpoints:

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/terms` | List terms (supports `q`, `status`, `category`, `limit`, `offset`) |
| `POST` | `/api/v1/terms` | Create a term |
| `GET` | `/api/v1/terms/{id}` | Get a term |
| `PUT` | `/api/v1/terms/{id}` | Update a term |
| `DELETE` | `/api/v1/terms/{id}` | Delete a term |
| `POST` | `/api/v1/terms/{id}/vote` | Vote for a term |
| `POST` | `/api/v1/terms/{id}/dispute` | Dispute a term |
| `POST` | `/api/v1/terms/{id}/official` | Mark official (editor+) |
| `POST` | `/api/v1/terms/{id}/promote` | Promote status (editor+) |
| `GET` | `/api/v1/terms/{id}/history` | View edit history |
| `GET` | `/api/v1/export` | Export as Markdown |
| `GET` | `/health` | Health check |
| `*` | `/mcp` | MCP endpoint (bearer auth) |

---

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for a full breakdown of the component structure, data model, and design decisions.

---

## License

[MIT](LICENSE)
