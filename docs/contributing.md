# Contributing

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.12+ | |
| [uv](https://docs.astral.sh/uv/) | latest | `brew install uv` on macOS. **Use `uv`, not `pip`.** |
| Node.js | 20+ | Frontend only |
| Docker | 20.10+ | Integration tests and local Postgres |

---

## Setting up locally

```bash
git clone https://github.com/schinnam/lingo
cd lingo

# Start Postgres
docker-compose up postgres -d

# Install dependencies and run migrations
uv sync
uv run alembic upgrade head

# Start the server
LINGO_DEV_MODE=true uv run uvicorn lingo.main:app --reload
```

Server: `http://localhost:8000` — `LINGO_DEV_MODE=true` disables auth so you can test without OIDC.

### Frontend development

Two modes:

=== "HMR (fast iteration)"
    ```bash
    cd frontend && npm install && npm run dev
    ```
    Runs a Vite dev server with hot module replacement. **Not served by FastAPI.**

=== "Production build"
    ```bash
    cd frontend && npm run build
    ```
    Output goes to `src/lingo/static/`. Served by FastAPI. Commit this if you changed the UI.

!!! note
    If you test via `http://localhost:8000` without rebuilding, you'll see stale output.

---

## Running tests

=== "Unit tests (no Docker)"
    ```bash
    make test-unit
    ```

=== "Integration tests (real Postgres)"
    ```bash
    make test-integration
    ```
    Spins up a Postgres container, creates `lingo_test`, runs Alembic migrations.

=== "All tests"
    ```bash
    make test
    ```

=== "Frontend tests"
    ```bash
    cd frontend && npm test
    ```

### Test approach

Follow red/green TDD: write a failing test first, then implement. PRs without tests for new behavior will be asked to add them before merge.

- **Backend unit tests** — `tests/unit/`, in-memory SQLite, no Docker required, fast
- **Backend integration tests** — `tests/integration/`, real Postgres via Docker
- **`asyncio_mode = "auto"`** — already set in `pyproject.toml`; don't add `@pytest.mark.asyncio` to every test
- **`LINGO_DEV_MODE=true`** — set automatically in test fixtures; `X-User-Id` auth works in tests, not in production

---

## Making changes

### Backend

- Keep async throughout — all database calls go through SQLAlchemy async sessions.
- New database columns require an Alembic migration:

    ```bash
    uv run alembic revision --autogenerate -m "describe the change"
    ```

    Review the generated file before committing — autogenerate misses check constraints and PostgreSQL-specific types.
- The scheduler runs in-process; keep scheduled jobs stateless and idempotent.
- New API endpoints must require authentication. Do not add unauthenticated endpoints without a strong reason.

### Frontend

- Components live in `frontend/src/components/`. Data fetching goes through TanStack Query hooks in `frontend/src/hooks/useTerms.ts`.
- Run `npm run lint` before pushing — ESLint is strict on React hooks rules.
- After UI changes, run `npm run build` to regenerate `src/lingo/static/`. Commit the built output.

### Migrations

Always write both `upgrade()` and `downgrade()` in migrations. Missing `downgrade()` that drops enum types causes "type already exists" errors on re-upgrade.

---

## Submitting a PR

1. Branch off `main`.
2. Keep PRs focused — one logical change per PR.
3. Update `CHANGELOG.md` under `## [Unreleased]` following the [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.
4. Ensure `make test` passes locally.

---

## Key gotchas

| Gotcha | Why it matters |
|---|---|
| Use `uv run` for all Python commands | Ensures the managed virtualenv is used, not system Python |
| `LINGO_DEV_MODE=true` is dev-only | Never set this in production — it disables auth entirely |
| `--workers 1` in production | APScheduler runs in-process; multiple workers cause duplicate job execution |
| Rebuild frontend after UI changes | `src/lingo/static/` is served directly by FastAPI — stale builds cause confusing behavior |
