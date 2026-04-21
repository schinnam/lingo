# Slack Bot

Lingo's Slack bot lets your team look up, add, and vote on terms without leaving Slack. It uses the Slack Events API via HTTPS.

---

## Setup

You can create the Slack app either by pasting an App Manifest (fastest) or by configuring each option manually.

### Option A — App Manifest (recommended)

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and click **Create New App → From an app manifest**.
2. Select your workspace and paste the YAML below.
3. Click **Next → Create**.

```yaml
display_information:
  name: Lingo
  description: Look up and manage your team's shared glossary

settings:
  org_deploy_enabled: false
  socket_mode_enabled: false
  token_rotation_enabled: false

features:
  bot_user:
    display_name: Lingo
    always_online: false
  slash_commands:
    - command: /lingo
      url: https://your-lingo-host/slack/events
      description: Look up or add a Lingo term
      usage_hint: "<term> | define <term> | add <TERM> -- <definition> | vote <term> | export | token [name]"
      should_escape: false
  events_api:
    request_url: https://your-lingo-host/slack/events
    bot_events:
      - message.channels
  interactivity:
    is_enabled: true
    request_url: https://your-lingo-host/slack/events

oauth_config:
  redirect_urls:
    - https://your-lingo-host/auth/slack/callback
  scopes:
    bot:
      - channels:history
      - chat:write
      - commands
      - users:read
    user:
      - openid
      - email
      - profile
```

Replace `https://your-lingo-host` with your server's public URL (must be HTTPS).

After the app is created:

1. **Install to workspace** → Go to **OAuth & Permissions → Install to Workspace**. Copy the **Bot User OAuth Token** — this is `LINGO_SLACK_BOT_TOKEN`.
2. **Copy the signing secret** → Go to **Basic Information → App Credentials** and copy **Signing Secret** — this is `LINGO_SLACK_SIGNING_SECRET`.
3. **Copy OAuth credentials** → From the same **Basic Information** page, copy **Client ID** and **Client Secret** — these are `LINGO_SLACK_CLIENT_ID` and `LINGO_SLACK_CLIENT_SECRET` (required for web UI login).

---

### Option B — Manual setup

#### 1. Create a Slack app

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and click **Create New App → From scratch**.
2. Name it `Lingo` and pick your workspace.

#### 2. Configure Events API

In the sidebar, go to **Event Subscriptions** and toggle it **On**.
1. **Request URL**: Enter `https://your-lingo-host/slack/events`.
2. **Subscribe to bot events**: Add `message.channels`.
3. Click **Save Changes**.

#### 3. Configure Interactivity

In the sidebar, go to **Interactivity & Shortcuts** and toggle it **On**.
1. **Request URL**: Enter `https://your-lingo-host/slack/events`.
2. Click **Save Changes**.

#### 4. Add Bot Token Scopes

Go to **OAuth & Permissions → Scopes → Bot Token Scopes** and add:

| Scope | Purpose |
|---|---|
| `commands` | Slash commands |
| `chat:write` | Send messages and DMs |
| `channels:history` | Auto-discovery job (reads public channel messages) |
| `users:read` | Resolve user info for DMs |

Also add the following **User Token Scopes** (required for web UI login via Sign in with Slack):

| Scope |
|---|
| `openid` |
| `email` |
| `profile` |

#### 5. Set the OAuth redirect URL

Go to **OAuth & Permissions → Redirect URLs** and add:

```
https://your-lingo-host/auth/slack/callback
```

#### 6. Add the slash command

Go to **Slash Commands → Create New Command**:

| Field | Value |
|---|---|
| Command | `/lingo` |
| Request URL | `https://your-lingo-host/slack/events` |
| Short Description | `Look up or add a Lingo term` |
| Usage Hint | `<term> \| define <term> \| add <TERM> -- <definition> \| vote <term> \| export \| token [name]` |

#### 7. Install to workspace

Go to **OAuth & Permissions → Install to Workspace**. Copy the **Bot User OAuth Token** — this is `LINGO_SLACK_BOT_TOKEN`.

#### 8. Configure Lingo

Set the environment variables and restart the server.

```bash
# Bot (required for Slack bot)
LINGO_SLACK_BOT_TOKEN=xoxb-...   # OAuth & Permissions -> Bot User OAuth Token
LINGO_SLACK_SIGNING_SECRET=...   # Basic Information -> App Credentials

# OAuth (required for web UI "Sign in with Slack")
LINGO_SLACK_CLIENT_ID=...        # Basic Information -> App Credentials
LINGO_SLACK_CLIENT_SECRET=...    # Basic Information -> App Credentials
```

If using Docker Compose:
```bash
docker compose up --build
```

---

## Testing

After completing setup and restarting the Lingo server, open any Slack channel and verify each integration surface:

### 1. Slash command responds

```
/lingo API
```

or the explicit form:

```
/lingo define API
```

Expected: Lingo replies with the term's name, definition, status, and vote count.

### 2. Add a term

```
/lingo add BART -- Bay Area Rapid Transit
```

Expected: Lingo confirms the term was created with `pending` status. This requires your Slack account to be linked to a Lingo account (log in via the web UI first).

### 3. Vote on a term

```
/lingo vote BART
```

Expected: Lingo confirms your vote and shows the updated vote count.

### 4. Generate an API token

```
/lingo token my-mcp-token
```

Expected: Lingo DMs you a one-time token string. **Copy it immediately** — it cannot be retrieved later. Use this token to authenticate CLI or MCP requests.

### 5. Export the glossary

```
/lingo export
```

Expected: Lingo uploads a Markdown-formatted list of all terms.

---

## Slash commands

### `/lingo <term>` — quick look up

```
/lingo API
```

Shorthand for `/lingo define <term>`. Type the term directly after `/lingo` — no subcommand needed.

---

### `/lingo define <term>` — look up a term

```
/lingo define API
```

Returns the term name, definition, status, and vote count. If no exact match is found, shows similar terms.

---

### `/lingo add <TERM> -- <definition>` — add a term

```
/lingo add BART -- Bay Area Rapid Transit
```

Creates a new term with `pending` status. Requires a linked Lingo account — anonymous Slack adds are rejected to prevent orphaned terms without a responsible owner.

---

### `/lingo vote <term>` — vote for a term

```
/lingo vote BART
```

Casts your vote. When the community threshold is reached, the term automatically advances to `community` status.

---

### `/lingo export` — export the glossary

```
/lingo export
```

Returns a Markdown-formatted export of all terms as a file upload.

---

## Notifications

The bot sends direct messages automatically in two cases:

**Dispute notification** — when someone disputes a term you own, you receive a DM with the term name and the disputing user.

**Staleness reminder** — the weekly staleness job DMs you when a term you own hasn't been confirmed in `LINGO_STALE_THRESHOLD_DAYS` (default: 180) days. The DM includes **Confirm** and **Update** buttons powered by Block Kit.

---

## Known limitations

**Public URL Required:** Unlike Socket Mode, the Events API requires your Lingo server to be reachable by Slack via a public HTTPS URL. For local development, use a tool like **ngrok** to expose your local port 8000: `ngrok http 8000`.

**Verification:** When setting the Request URL in the Slack dashboard, Slack sends a `url_verification` challenge. Lingo handles this automatically, but the server must be running and reachable when you click "Save".

---

## Auto-discovery

The daily discovery job (runs at 2 AM) scans public Slack channels over a 90-day window, extracts uppercase acronyms matching `[A-Z]{2,6}`, and creates `suggested` terms for any not already in the glossary. This surfaces jargon your team is already using without requiring anyone to add it manually.
