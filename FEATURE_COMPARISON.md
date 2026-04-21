# Feature Comparison: API · Web · CLI · Slack · MCP

Use this table to identify gaps across surfaces and decide what to build or backlog.

**Symbols:** ✅ supported · ❌ not supported · ⚠️ partial/limited · N/A not applicable

> The **API** column represents the raw REST API (`/api/v1/`). It is the canonical backend that all other surfaces call. Comparing it against client surfaces reveals endpoints that exist but are unreachable without hitting the API directly.

---

## Feature Matrix

| Domain | Feature | API | Web | CLI | Slack | MCP |
|--------|---------|:---:|:---:|:---:|:-----:|:---:|
| **Discovery & Browse** | Full-text search | ✅ | ✅ | ❌ | ❌ | ✅ |
| | Name lookup (exact) | ✅ | ✅ | ✅ | ✅ | ✅ |
| | List terms | ✅ | ✅ | ✅ | ❌ | ✅ |
| | Filter by status | ✅ | ✅ | ✅ | ❌ | ✅ |
| | Filter by category | ✅ | ✅ | ✅ | ❌ | ✅ |
| | Pagination | ✅ | ✅ | ⚠️ `--limit` only | ❌ | ✅ |
| | Export as Markdown | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Term Management** | Add term | ✅ | ✅ | ✅ | ✅ | ❌ |
| | Direct edit (definition / full name / category) | ✅ | ❌ † | ❌ | ❌ | ❌ |
| | Delete term (admin) | ✅ | ✅ | ❌ | ❌ | ❌ |
| | Claim ownership | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Voting & Governance** | Vote for term | ✅ | ✅ | ❌ | ✅ | ❌ |
| | Mark as official (editor) | ✅ | ✅ | ❌ | ❌ | ❌ |
| | Promote status (editor) | ✅ | ✅ | ❌ | ❌ | ❌ |
| | Dismiss / archive (editor) | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Suggestions** | Suggest a definition | ✅ | ✅ | ❌ | ❌ | ❌ |
| | View pending suggestions | ✅ | ✅ | ❌ | ❌ | ❌ |
| | Accept suggestion | ✅ | ✅ | ❌ | ❌ | ❌ |
| | Reject suggestion | ✅ | ✅ | ❌ | ❌ | ❌ |
| **History & Versions** | View edit history | ✅ | ✅ | ❌ | ❌ | ❌ |
| | Revert to previous version (editor) | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Relationships** | View relationships | ✅ | ✅ | ❌ | ❌ | ❌ |
| | Add relationship (editor) | ✅ | ✅ | ❌ | ❌ | ❌ |
| | Remove relationship (editor) | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Staleness** | View stale status | ✅ | ✅ | ❌ | ❌ | ❌ |
| | Confirm term freshness | ✅ | ✅ | ❌ | ✅ interactive DM | ❌ |
| | Receive staleness alerts | N/A | ❌ | ❌ | ✅ DM | N/A |
| **Auth & Tokens** | Login / authenticate | ✅ | ✅ Slack OIDC | ⚠️ dev mode only | N/A | N/A |
| | Generate API token | ✅ | ✅ | ❌ | ✅ | ❌ |
| | List own tokens | ✅ | ✅ | ❌ | ❌ | ❌ |
| | Revoke token | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Admin** | View user list | ✅ | ✅ | ❌ | ❌ | ❌ |
| | Change user roles | ✅ | ✅ | ❌ | ❌ | ❌ |
| | View audit log | ✅ | ✅ | ❌ | ❌ | ❌ |
| | View system stats | ✅ | ✅ | ❌ | ❌ | ❌ |
| | Trigger discovery job | ✅ | ✅ | ❌ | ❌ | ❌ |
| | Trigger staleness job | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Notifications** | Suggestion received (owner DM) | N/A | N/A | N/A | ✅ | N/A |
| | Status promotion (channel post) | N/A | N/A | N/A | ✅ | N/A |
| | Staleness reminder (owner DM) | N/A | N/A | N/A | ✅ | N/A |

† `PUT /api/v1/terms/{id}` exists and supports direct field edits with optimistic concurrency, but the Web UI intentionally routes definition changes through the suggestion-accept flow instead. The raw PUT endpoint is effectively **API-only** with no first-party client surface.

---

## API Endpoints With No Client Surface

These endpoints exist in the REST API but are not exposed through any of the four surfaces above. They are only reachable by calling the API directly (e.g. via `curl` with an API token).

| Endpoint | Description | Potential action |
|----------|-------------|-----------------|
| `PUT /api/v1/terms/{id}` | Direct term edit (definition, full\_name, category) | Add to CLI as `lingo edit`; or document as intentional API-only |
| `GET /api/v1/features` | Feature flag state | Used only by Web; could expose via `lingo features` in CLI for debugging |

---

## Gap Summary by Surface

### CLI — most gaps
Missing features relative to what the API supports:
- Full-text search (only exact name lookup via `lingo define`)
- Vote for a term
- Edit a term directly
- Delete a term
- Suggestions workflow (suggest, view, accept, reject)
- Edit history and revert
- Relationships (view / add / remove)
- Staleness confirmation
- Token management (generate, list, revoke)
- Admin operations

**High-value additions:** `lingo vote`, `lingo edit`, `lingo suggest` would bring CLI closer to parity for day-to-day power users.

### Slack — collaboration-focused but limited browsing
Missing features:
- List / browse / filter terms
- Direct term editing
- Suggestions workflow (owners get a DM notification but cannot act on suggestions from Slack)
- Edit history and revert
- Relationships
- Admin controls
- Token revocation

**High-value additions:** `/lingo suggest <term> -- <new-definition>` and `/lingo list` would close the most-felt gaps without overloading the Slack UX.

### MCP — intentionally read-only
Read-only by design to preserve the community voting lifecycle. Missing:
- Any write operation (add, edit, vote, suggest)
- Export
- Staleness confirmation

**Consider:** `add_term` and `vote_term` tools if AI-agent-driven glossary population becomes a use case. Keep writes gated behind the voting workflow.

### Web — missing proactive reach
The only gap relative to other surfaces:
- No proactive notifications (staleness alerts, suggestion DMs) — Slack-only today

**Consider:** In-app notification badge or email digest if users don't have Slack.
