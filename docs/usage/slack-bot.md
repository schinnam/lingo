# Slack Bot

Lingo's Slack bot lets your team look up, add, and vote on terms without leaving Slack. It uses Socket Mode — no public URL or webhook configuration required.

---

## Setup

### 1. Create a Slack app

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and click **Create New App → From scratch**.
2. Name it `Lingo` and pick your workspace.

### 2. Enable Socket Mode

In the sidebar, go to **Socket Mode** and toggle it on. Generate an **App-Level Token** with the `connections:write` scope. This becomes `LINGO_SLACK_APP_TOKEN`.

### 3. Add Bot Token Scopes

Go to **OAuth & Permissions → Scopes → Bot Token Scopes** and add:

| Scope | Purpose |
|---|---|
| `commands` | Slash commands |
| `chat:write` | Send messages and DMs |
| `channels:history` | Auto-discovery job (reads public channel messages) |
| `users:read` | Resolve user info for DMs |

### 4. Add the slash command

Go to **Slash Commands → Create New Command**:

| Field | Value |
|---|---|
| Command | `/lingo` |
| Request URL | `https://example.com/slack` (placeholder — Socket Mode ignores this) |
| Short Description | `Look up or add a Lingo term` |

### 5. Install to workspace

Go to **OAuth & Permissions → Install to Workspace**. Copy the **Bot User OAuth Token** — this is `LINGO_SLACK_BOT_TOKEN`.

### 6. Configure Lingo

Set the three environment variables and restart the server:

```bash
LINGO_SLACK_BOT_TOKEN=xoxb-...
LINGO_SLACK_APP_TOKEN=xapp-...
LINGO_SLACK_SIGNING_SECRET=...   # from Basic Information → App Credentials
```

---

## Slash commands

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

Creates a new term with `suggested` status. Requires a linked Lingo account — anonymous Slack adds are rejected to prevent orphaned terms without a responsible owner.

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

Returns a Markdown-formatted export of all `official` terms as a Slack message.

---

## Notifications

The bot sends direct messages automatically in two cases:

**Dispute notification** — when someone disputes a term you own, you receive a DM with the term name and the disputing user.

**Staleness reminder** — the weekly staleness job DMs you when a term you own hasn't been confirmed in `LINGO_STALE_THRESHOLD_DAYS` (default: 180) days. The DM includes **Confirm** and **Update** buttons powered by Block Kit.

---

## Auto-discovery

The daily discovery job (runs at 2 AM) scans public Slack channels over a 90-day window, extracts uppercase acronyms matching `[A-Z]{2,6}`, and creates `suggested` terms for any not already in the glossary. This surfaces jargon your team is already using without requiring anyone to add it manually.
