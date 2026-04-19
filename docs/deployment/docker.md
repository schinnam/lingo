# Docker

Lingo ships as a single Docker image containing the Python backend and pre-built React frontend. PostgreSQL is not included — use the compose file or provide your own.

---

## Docker Compose (quickest)

The repository includes a `docker compose.yml` that starts PostgreSQL and Lingo together:

```bash
git clone https://github.com/schinnam/lingo
cd lingo
docker compose up
```

Server: `http://localhost:8000`

The compose file sets `LINGO_DEV_MODE=true` by default. This is fine for local exploration but **must be disabled for production**.

### Run in the background

```bash
docker compose up -d
docker compose logs -f lingo
```

### Stop

```bash
docker compose down
```

---

## Build the image

```bash
docker build -t lingo .
```

The Dockerfile uses `python:3.12-slim` as a base, installs dependencies with `uv`, and copies the pre-built frontend from `src/lingo/static/`. The final image runs as a non-root user (`appuser`, UID 1001).

---

## Run with Docker

### Run database migrations first

Always run migrations before starting the server (first boot and after each upgrade):

```bash
docker run --rm \
  -e LINGO_DATABASE_URL=postgresql+asyncpg://user:pass@db-host:5432/lingo \
  lingo \
  uv run alembic upgrade head
```

### Start the server

```bash
docker run -p 8000:8000 \
  -e LINGO_DATABASE_URL=postgresql+asyncpg://user:pass@db-host:5432/lingo \
  -e LINGO_SECRET_KEY=your-secret \
  -e LINGO_DEV_MODE=false \
  lingo
```

!!! warning "`--workers 1` is required"
    APScheduler runs in-process and shares the FastAPI event loop. Multiple workers would each start their own scheduler and run jobs multiple times.

    The Dockerfile's default `CMD` already sets `--workers 1`. Do not override this.

---

## Environment variables via compose override

For development environments with different settings, use a `docker compose.override.yml`:

```yaml
services:
  lingo:
    environment:
      LINGO_DEV_MODE: "false"
      LINGO_SECRET_KEY: "local-dev-secret"
      # LINGO_SLACK_CLIENT_ID: "your-slack-client-id"
      # LINGO_SLACK_CLIENT_SECRET: "your-slack-client-secret"
      LINGO_SLACK_BOT_TOKEN: "xoxb-..."
```

---

## Health check

```bash
curl http://localhost:8000/health
```

Returns `{"status": "ok"}` when the server is running.

---

## Next steps

- [Production deployment](production.md) — security checklist, Slack auth, scaling
- [Configuration](../getting-started/configuration.md) — all environment variables
