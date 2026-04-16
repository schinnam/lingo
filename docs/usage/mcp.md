# MCP / AI Agents

Lingo exposes a [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server at `/mcp`. This lets Claude and other MCP-aware AI agents look up internal terms automatically during conversations.

---

## Setup

### 1. Generate a bearer token

MCP authentication uses the same API token system as the REST API. Tokens are stored as SHA-256 hashes and shown only once at creation time.

**Option A — via Slack:**

```
/lingo token my-claude-token
```

Lingo DMs you the raw token. Copy it immediately.

**Option B — via REST API** (requires an existing session):

```bash
curl -s -X POST https://your-lingo-host/api/v1/tokens \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-session-token>" \
  -d '{"name": "my-claude-token", "scopes": ["read"]}'
```

The response contains a `token` field with the raw value. **Store it now** — it cannot be retrieved later.

```json
{
  "id": "...",
  "name": "my-claude-token",
  "scopes": ["read"],
  "user_id": "...",
  "token": "abc123..."
}
```

**Option C — via dev mode** (local development only):

```bash
# Start a session with dev login, then create a token
curl -s "http://localhost:8000/auth/dev/login?email=you@example.com" -c cookies.txt
curl -s -X POST http://localhost:8000/api/v1/tokens \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"name": "local-mcp", "scopes": ["read"]}'
```

### 2. Configure Claude Desktop

Edit `claude_desktop_config.json` (usually at `~/Library/Application Support/Claude/` on macOS):

```json
{
  "mcpServers": {
    "lingo": {
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer <your-token>"
      }
    }
  }
}
```

Replace `http://localhost:8000` with your server's public URL for production use, and `<your-token>` with the token generated in step 1.

Restart Claude Desktop. Lingo's tools will appear in the MCP tools list.

---

## Available tools

### `get_term`

Exact case-insensitive lookup by name.

```
get_term(name: "API")
```

Returns: name, full name, definition, category, status, vote count.

Returns an error if the term is not found.

**Example prompts that trigger this tool:**

- "What does SLA mean in this company?"
- "Define BART for me."
- "Look up the term OKR in Lingo."

---

### `search_terms`

Full-text search across term name, definition, and full name.

```
search_terms(query: "service level", status: "official", limit: 5)
```

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `query` | string | Yes | — | Search string |
| `status` | string | No | (all) | Filter by status |
| `limit` | integer | No | 10 | Maximum results |

Returns a list of matching terms.

**Example prompts that trigger this tool:**

- "Find all terms related to monitoring."
- "Search Lingo for anything about incident response."
- "Are there any official terms about data pipelines?"

---

### `list_terms`

Paginated list of terms with optional filters.

```
list_terms(category: "tech", status: "official", limit: 20, offset: 0)
```

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `category` | string | No | (all) | Filter by category |
| `status` | string | No | (all) | Filter by status |
| `limit` | integer | No | 50 | Page size |
| `offset` | integer | No | 0 | Pagination offset |

**Example prompts that trigger this tool:**

- "List all official terms in the engineering category."
- "Show me the first 10 terms in the glossary."
- "What terms are currently in suggested status?"

---

## Why MCP is read-only

The MCP endpoint exposes only read operations. Write operations (adding terms, voting) require going through the REST API or Slack bot, where user identity and authorization are well-defined.

Allowing AI agents to add or modify terms would bypass the community vote-based governance model that gives each term its legitimacy. The `suggested → pending → community → official` lifecycle exists precisely to ensure human review and endorsement.

---

## Authentication

All requests to `/mcp` must include the `Authorization: Bearer <token>` header. The `MCPBearerAuthMiddleware` validates this against `LINGO_MCP_BEARER_TOKEN` before passing the request to the FastMCP app.

Requests without a valid token receive `401 Unauthorized`.

---

## Using with other MCP clients

Lingo's MCP server uses the HTTP/Streamable transport and is compatible with any MCP client that supports it. Configure the server URL as `http://your-host:8000/mcp` and provide the bearer token in the `Authorization` header.
