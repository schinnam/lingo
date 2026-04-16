# Configuration

All settings use the `LINGO_` prefix. Set them as environment variables or in a `.env` file at the project root.

---

## Core settings

| Variable | Default | Description |
|---|---|---|
| `LINGO_DATABASE_URL` | `postgresql+asyncpg://lingo:lingo@localhost:5432/lingo` | PostgreSQL connection string. Must use the `asyncpg` driver. |
| `LINGO_SECRET_KEY` | `change-me-in-production` | JWT signing key. Use a long random string in production. |
| `LINGO_APP_URL` | `http://localhost:8000` | Public base URL. Used for CORS headers and Slack notification links. |
| `LINGO_DEV_MODE` | `false` | Enables dev-only auth bypasses. **Never enable in production.** |

### `LINGO_SECRET_KEY` — generation and rotation

!!! warning "Change `LINGO_SECRET_KEY` before deploying"
    The default value is public. Anyone who knows it can forge valid JWTs. Generate a strong random key and keep it secret.

**Generate a key:**

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**Rotate the key:**

Changing `LINGO_SECRET_KEY` immediately invalidates all existing JWT sessions (web UI logins). API tokens stored in the database are unaffected — they are validated by hash lookup, not JWT signature. To rotate:

1. Generate a new key with the command above.
2. Update `LINGO_SECRET_KEY` in your environment or `.env` file.
3. Restart the server.
4. Users will be asked to log in again via Slack OAuth.

---

### `LINGO_DEV_MODE` — development auth bypass

When `LINGO_DEV_MODE=true`, two additional authentication paths are enabled:

**Email-based dev login** — visit this URL to create or log in as any user by email, with no credential check:

```
http://localhost:8000/auth/dev/login?email=you@example.com
```

**`X-User-Id` header** — pass a user UUID directly in any API request:

```bash
curl http://localhost:8000/api/v1/terms \
  -H "X-User-Id: <user-uuid>"
```

Both bypasses are completely disabled when `LINGO_DEV_MODE=false`. Never set this to `true` in production — it allows anyone to authenticate as any user.

---

## Slack OAuth

| Variable | Default | Description |
|---|---|---|
| `LINGO_SLACK_CLIENT_ID` | `""` | Client ID from your Slack app's **Basic Information** page. Required for web UI login. |
| `LINGO_SLACK_CLIENT_SECRET` | `""` | Client Secret from your Slack app's **Basic Information** page. |

The web UI uses **Sign in with Slack** (OpenID Connect) for authentication. See the [Slack Bot guide](../usage/slack-bot.md) for app creation steps.

### OIDC flow walkthrough

Understanding how Slack OIDC works helps with debugging redirect errors and misconfigured scopes.

**1. Login initiation** (`GET /auth/slack/login`)

Lingo generates a cryptographic nonce, signs it with HMAC-SHA256 using `LINGO_SECRET_KEY`, and stores the unsigned nonce in a short-lived HTTP-only cookie (5-minute expiry). The user is redirected to Slack's OAuth endpoint with:

- `client_id` = `LINGO_SLACK_CLIENT_ID`
- `scope` = `openid email profile`
- `redirect_uri` = `LINGO_APP_URL/auth/slack/callback`
- `state` = the signed nonce (tamper-evident)

**2. Slack authentication**

The user approves the Lingo app in Slack's UI. Slack redirects back to `redirect_uri` with a short-lived `code` and the original `state`.

**3. Callback validation** (`GET /auth/slack/callback`)

Lingo validates the `state` using `hmac.compare_digest()` (timing-safe) against the cookie. If validation passes, Lingo exchanges the `code` for tokens via `https://slack.com/api/openid.connect.token`, then fetches the user profile via `https://slack.com/api/openid.connect.userInfo`.

**4. User provisioning**

Lingo looks up an existing user by `slack_user_id`, then by email, and creates one if neither matches. The user's session cookie (`user_id`) is set with a 24-hour expiry (HTTPS-only in production).

**Common errors:**

| Error | Likely cause |
|---|---|
| `redirect_uri_mismatch` | The redirect URL in your Slack app doesn't match `LINGO_APP_URL/auth/slack/callback`. |
| `invalid_client` | Wrong `LINGO_SLACK_CLIENT_ID` or `LINGO_SLACK_CLIENT_SECRET`. |
| `state mismatch` | Clock skew or cookie not sent (check `LINGO_APP_URL` uses HTTPS in production). |
| 401 after login | User account exists but `is_active=false`. |

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
