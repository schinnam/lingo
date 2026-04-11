# Production Deployment

This guide covers running Lingo safely in a production environment.

---

## Security checklist

Before going live, verify each of these:

- [ ] `LINGO_DEV_MODE=false` — this disables the `X-User-Id` header auth bypass
- [ ] `LINGO_SECRET_KEY` is a long, random, secret value (not the default `change-me-in-production`)
- [ ] `LINGO_APP_URL` is set to your public URL (e.g. `https://lingo.example.com`) — controls CORS
- [ ] Database credentials are strong and not the defaults
- [ ] The Lingo container is not exposing port 5432 (Postgres) to the public internet
- [ ] `LINGO_MCP_BEARER_TOKEN` is set if you're using the MCP endpoint
- [ ] `LINGO_SLACK_CLIENT_ID` is set (required for web UI login)
- [ ] `LINGO_SLACK_CLIENT_SECRET` is set (required for web UI login)
- [ ] TLS/HTTPS is terminated at a reverse proxy (nginx, Caddy, etc.) in front of Lingo

---

## Generating a secret key

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Use the output as `LINGO_SECRET_KEY`. Store it in a secrets manager — do not commit it to version control.

---

## Running with Docker

### 1. Run migrations

Always run migrations before starting the server, especially on first boot or after an upgrade:

```bash
docker run --rm \
  -e LINGO_DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/lingo \
  lingo \
  uv run alembic upgrade head
```

### 2. Start the server

```bash
docker run -d -p 8000:8000 \
  -e LINGO_DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/lingo \
  -e LINGO_SECRET_KEY=your-very-long-random-key \
  -e LINGO_DEV_MODE=false \
  -e LINGO_APP_URL=https://lingo.example.com \
  --name lingo \
  lingo
```

---

## Slack Auth

Lingo uses **Sign in with Slack** for web UI authentication. Set up a Slack app before going live:

1. Create or open your Slack app at [https://api.slack.com/apps](https://api.slack.com/apps)
2. Under **OAuth & Permissions**, add a redirect URI:
   `https://<your-domain>/auth/slack/callback`
3. Under **OAuth & Permissions → OpenID Connect Scopes**, add: `openid`, `email`, `profile`
4. Copy **Client ID** and **Client Secret** from **Basic Information**

Set the credentials as environment variables:

```bash
LINGO_SLACK_CLIENT_ID=your-client-id
LINGO_SLACK_CLIENT_SECRET=your-client-secret
```

!!! note
    Bot scopes (`commands`, `chat:write`) and Sign in with Slack (`openid`) are separate flows on the same Slack app. Both can coexist in one app configuration.

    Users without Slack can still access Lingo via the CLI or MCP endpoint using API tokens.

---

## Reverse proxy

Lingo does not terminate TLS. Run it behind nginx, Caddy, or a cloud load balancer.

**nginx example:**

```nginx
server {
    listen 443 ssl;
    server_name lingo.example.com;

    ssl_certificate     /etc/ssl/certs/lingo.crt;
    ssl_certificate_key /etc/ssl/private/lingo.key;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}
```

**Caddy example:**

```
lingo.example.com {
    reverse_proxy localhost:8000
}
```

---

## Scheduler requirements

The APScheduler runs two background jobs in-process:

- **DiscoveryJob** — daily at 2 AM (scans Slack for new acronyms)
- **StalenessJob** — weekly on Monday at 3 AM (DMs owners of stale terms)

APScheduler shares the FastAPI event loop. **You must run with `--workers 1`** to prevent each worker process from starting its own scheduler and running jobs multiple times. The default `CMD` in the Dockerfile already enforces this.

---

## Updating Lingo

1. Pull the new image: `docker pull lingo` (or rebuild)
2. Run migrations: `docker run --rm -e LINGO_DATABASE_URL=... lingo uv run alembic upgrade head`
3. Restart the container: `docker stop lingo && docker run ...` (or `docker-compose up -d`)

Always run migrations before restarting the server after an upgrade.

---

## Monitoring

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness check — returns `{"status":"ok"}` |
| `GET /api/v1/admin/stats` | Term/user counts (requires admin token) |
| `GET /api/v1/admin/jobs` | Scheduler job history (requires admin token) |

Wire `/health` to your uptime monitoring or load balancer health checks.
