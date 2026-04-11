# Configuration

All settings use the `LINGO_` prefix. Set them as environment variables or in a `.env` file at the project root.

---

## Core settings

| Variable | Default | Description |
|---|---|---|
| `LINGO_DATABASE_URL` | `postgresql+asyncpg://lingo:lingo@localhost:5432/lingo` | PostgreSQL connection string. Must use the `asyncpg` driver. |
| `LINGO_SECRET_KEY` | `change-me-in-production` | JWT signing key. Use a long random string in production. |
| `LINGO_APP_URL` | `http://localhost:8000` | Public base URL. Used for CORS headers and Slack notification links. |
| `LINGO_DEV_MODE` | `false` | Enables `X-User-Id` header auth. **Never enable in production.** |

!!! warning "Change `LINGO_SECRET_KEY` before deploying"
    The default value is public. Anyone who knows it can forge valid JWTs. Generate a strong random key and keep it secret.

    ```bash
    python3 -c "import secrets; print(secrets.token_hex(32))"
    ```

---

## Slack OAuth

| Variable | Default | Description |
|---|---|---|
| `LINGO_SLACK_CLIENT_ID` | `""` | Client ID from your Slack app's **Basic Information** page. Required for web UI login. |
| `LINGO_SLACK_CLIENT_SECRET` | `""` | Client Secret from your Slack app's **Basic Information** page. |

The web UI uses **Sign in with Slack** for authentication. See [Production Deployment](../deployment/production.md) for Slack app setup steps.

!!! tip "Dev mode login"
    When `LINGO_DEV_MODE=true`, you can log in without Slack by visiting:
    `http://localhost:8000/auth/dev/login?email=you@example.com`

    Users without Slack can always authenticate via CLI or MCP using API tokens — only the web UI requires Slack.

---

## Slack bot

| Variable | Default | Description |
|---|---|---|
| `LINGO_SLACK_BOT_TOKEN` | `""` | Bot token (starts with `xoxb-`). From your Slack app's **OAuth & Permissions** page. |
| `LINGO_SLACK_APP_TOKEN` | `""` | App-level token (starts with `xapp-`). Required for Socket Mode. |
| `LINGO_SLACK_SIGNING_SECRET` | `""` | Signing secret from your Slack app's **Basic Information** page. |

All three are required to enable the Slack bot. See the [Slack Bot guide](../usage/slack-bot.md) for setup instructions.

---

## MCP server

| Variable | Default | Description |
|---|---|---|
| `LINGO_MCP_BEARER_TOKEN` | `""` | Bearer token required on the `Authorization` header for all `/mcp` requests. |

See the [MCP guide](../usage/mcp.md) for Claude Desktop configuration.

---

## Term governance

| Variable | Default | Description |
|---|---|---|
| `LINGO_COMMUNITY_THRESHOLD` | `3` | Number of votes needed to promote a term from `pending` → `community`. |
| `LINGO_OFFICIAL_THRESHOLD` | `10` | Number of votes needed for an editor to mark a term `community` → `official`. |
| `LINGO_STALE_THRESHOLD_DAYS` | `180` | Days since last confirmation before a term is flagged as stale. |

---

## Example `.env` file

```dotenv
# Core
LINGO_DATABASE_URL=postgresql+asyncpg://lingo:mysecretpassword@db:5432/lingo
LINGO_SECRET_KEY=a-very-long-random-string-change-me
LINGO_APP_URL=https://lingo.example.com
LINGO_DEV_MODE=false

# Slack OAuth (required for web UI login)
LINGO_SLACK_CLIENT_ID=your-slack-client-id
LINGO_SLACK_CLIENT_SECRET=your-slack-client-secret

# Slack bot (optional)
LINGO_SLACK_BOT_TOKEN=xoxb-...
LINGO_SLACK_APP_TOKEN=xapp-...
LINGO_SLACK_SIGNING_SECRET=...

# MCP (optional)
LINGO_MCP_BEARER_TOKEN=your-mcp-token

# Governance thresholds
LINGO_COMMUNITY_THRESHOLD=3
LINGO_OFFICIAL_THRESHOLD=10
LINGO_STALE_THRESHOLD_DAYS=180
```
