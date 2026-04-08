# Quickstart

Get Lingo running and add your first term in under five minutes.

## 1. Start the server

```bash
git clone https://github.com/schinnam/lingo
cd lingo
docker-compose up
```

Wait for the log line `Application startup complete.` The server is now at `http://localhost:8000`.

!!! note "Dev mode"
    The Docker Compose file sets `LINGO_DEV_MODE=true`. This disables authentication so you can explore without configuring OIDC or creating tokens. Never enable dev mode in production.

---

## 2. Open the web UI

Navigate to `http://localhost:8000` in your browser. You'll see the term browser — initially empty.

---

## 3. Add your first term

Click **Add term** and fill in:

| Field | Example |
|---|---|
| **Name** | `API` |
| **Definition** | `Application Programming Interface — a contract between software components` |
| **Full name** (optional) | `Application Programming Interface` |
| **Category** (optional) | `tech` |

Click **Add**. Your term is created with status `suggested`.

---

## 4. Vote it up

Find your term in the list and click **Vote**. Once enough team members vote, the status advances automatically:

```
suggested  →  pending  →  community  →  official
              (1 vote)   (3 votes)    (editor + 10 votes)
```

---

## 5. Try the CLI

Install the CLI and look up the term you just added:

```bash
uv pip install -e .
export LINGO_APP_URL=http://localhost:8000
export LINGO_DEV_USER_ID=00000000-0000-0000-0000-000000000001   # any UUID in dev mode

lingo define API
```

---

## 6. Try MCP with Claude

If you use Claude Desktop, add Lingo as an MCP server. Edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "lingo": {
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer your-mcp-token"
      }
    }
  }
}
```

Set `LINGO_MCP_BEARER_TOKEN=your-mcp-token` in your environment and restart the server. Claude can now call `get_term`, `search_terms`, and `list_terms` against your glossary.

---

## What's next

- [Configuration](configuration.md) — all `LINGO_*` environment variables
- [Slack Bot](../usage/slack-bot.md) — add and look up terms from Slack
- [Deployment](../deployment/docker.md) — run in production with real auth
