# MCP / AI Agents

Lingo exposes a [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server at `/mcp`. This lets Claude and other MCP-aware AI agents look up internal terms automatically during conversations.

---

## Setup

### 1. Set a bearer token

Choose a secret token and set it on the server:

```bash
LINGO_MCP_BEARER_TOKEN=your-secret-token
```

Restart the server after changing this value.

### 2. Configure Claude Desktop

Edit `claude_desktop_config.json` (usually at `~/Library/Application Support/Claude/` on macOS):

```json
{
  "mcpServers": {
    "lingo": {
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer your-secret-token"
      }
    }
  }
}
```

Replace `http://localhost:8000` with your server's public URL for production use.

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
