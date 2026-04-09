# Lingo

**Self-hosted company glossary. Slack, CLI, web UI, and AI agents — all from one service.**

Teams accumulate jargon fast. Lingo is where you put it. Add a term from Slack, vote it up, and AI agents can look it up via MCP. Stale terms get a nudge. The whole thing runs on Postgres.

[Get started](getting-started/quickstart.md) | [View on GitHub](https://github.com/schinnam/lingo)

---

## Features

| Surface | What it does |
|---|---|
| **Web UI** | Searchable term browser with status filters, voting, dispute actions, and a slide-in detail panel |
| **Slack Bot** | `/lingo define`, `/lingo add`, `/lingo vote`, `/lingo export` — look up and contribute terms without leaving Slack |
| **CLI** | `lingo define`, `lingo add`, `lingo list`, `lingo export` — terminal access to the full glossary |
| **REST API** | Full CRUD at `/api/v1/terms` with JWT / OIDC auth and interactive OpenAPI docs at `/docs` |
| **MCP Server** | `get_term`, `search_terms`, `list_terms` tools for Claude and other MCP-aware AI agents |
| **Auto-Discovery** | Daily job scans Slack for unknown acronyms and creates `suggested` terms automatically |
| **Staleness Tracking** | Weekly job DMs term owners when a term hasn't been confirmed in 180 days |
| **Self-Hosted** | One `docker-compose up` and you're running. PostgreSQL + Lingo, no external dependencies |

---

## Term lifecycle

Every term flows through four community-driven statuses:

```
suggested  →  pending  →  community  →  official
              ↑                ↑
        (first vote)   (community_threshold votes)
                                           ↓
                              (editor action at official_threshold)
```

- **suggested** — discovered by auto-scan or added without votes
- **pending** — at least one community vote
- **community** — vote count reached `LINGO_COMMUNITY_THRESHOLD` (default: 3)
- **official** — editor-approved, vote count reached `LINGO_OFFICIAL_THRESHOLD` (default: 10)

---

## Quickstart

```bash
git clone https://github.com/schinnam/lingo
cd lingo
docker-compose up
```

Open `http://localhost:8000`. Dev mode is on by default in the compose file, so no auth is required.

→ See the full [Quickstart guide](getting-started/quickstart.md) for next steps.

---

## Project info

| | |
|---|---|
| **Version** | 0.5.5 |
| **Language** | Python 3.12+ |
| **Framework** | FastAPI + React |
| **Database** | PostgreSQL 14+ |
| **License** | See repository |
| **Source** | [github.com/schinnam/lingo](https://github.com/schinnam/lingo) |
