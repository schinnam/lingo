# API Reference

Lingo's REST API is fully documented via OpenAPI. When the server is running, visit `/docs` for an interactive interface where you can try every endpoint directly from the browser.

```
http://localhost:8000/docs
```

---

## Authentication

All endpoints (except `/health`) require authentication. Include the token in the `Authorization` header:

```http
Authorization: Bearer <your-token>
```

In dev mode (`LINGO_DEV_MODE=true`), you may instead use:

```http
X-User-Id: <any-uuid>
```

!!! warning
    `X-User-Id` authentication is rejected with `401 Unauthorized` when `LINGO_DEV_MODE=false`.

---

## Endpoints

### Terms

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/terms` | List terms. Supports `q`, `status`, `category`, `limit`, `offset` query params. Returns `{items, total, offset, limit, counts_by_status}`. |
| `POST` | `/api/v1/terms` | Create a term. Body: `{name, definition, full_name?, category?}`. |
| `GET` | `/api/v1/terms/{id}` | Get a single term by UUID. |
| `PUT` | `/api/v1/terms/{id}` | Update a term. Requires `version` field for optimistic concurrency (returns `409` on mismatch). |
| `DELETE` | `/api/v1/terms/{id}` | Delete a term (editor+). |
| `POST` | `/api/v1/terms/{id}/vote` | Vote for a term. Deduped — one vote per user per term. |
| `POST` | `/api/v1/terms/{id}/dispute` | Dispute a term. Resets vote tally and notifies the owner. |
| `POST` | `/api/v1/terms/{id}/official` | Mark a term official (editor+). |
| `POST` | `/api/v1/terms/{id}/promote` | Manually promote a term's status (editor+). |
| `GET` | `/api/v1/terms/{id}/history` | Retrieve the append-only edit history for a term. |

### Export

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/export` | Export terms as Markdown. Supports `status` (default: `official`), `limit`, `offset`. Auth required. |

### Users

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/users` | List users (admin only). |
| `PATCH` | `/api/v1/users/{id}/role` | Update a user's role (admin only). Roles: `viewer`, `editor`, `admin`. |

### Tokens

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/tokens` | List your API tokens. |
| `POST` | `/api/v1/tokens` | Create an API bearer token. |
| `DELETE` | `/api/v1/tokens/{id}` | Revoke a token. |

### Admin

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/admin/stats` | Term and user counts (admin only). |
| `GET` | `/api/v1/admin/jobs` | Scheduler job run history (admin only). |
| `POST` | `/api/v1/admin/jobs/{job_type}/run` | Manually trigger a scheduler job (admin only). |
| `GET` | `/api/v1/admin/audit` | List audit events (admin only). |

### Other

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check. Returns `{"status": "ok"}`. No auth required. |
| `*` | `/mcp` | MCP endpoint — see [MCP / AI Agents](../usage/mcp.md). |

---

## Common response shapes

### Term list (`GET /api/v1/terms`)

```json
{
  "items": [...],
  "total": 42,
  "offset": 0,
  "limit": 50,
  "counts_by_status": {
    "suggested": 5,
    "pending": 8,
    "community": 12,
    "official": 17
  }
}
```

### Vote response (`POST /api/v1/terms/{id}/vote`)

```json
{
  "vote_count": 4,
  "transition": "to_community"
}
```

`transition` is `null` if no status change occurred, or one of `"to_pending"`, `"to_community"`, `"to_official"`.

---

## Optimistic concurrency

`PUT /api/v1/terms/{id}` requires a `version` field in the request body. If the version doesn't match the current row, the server returns `409 Conflict`. Fetch the latest term first, include its `version`, then submit your update.

This prevents silent overwrites when two editors update the same term concurrently.
