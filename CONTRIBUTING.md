# Contributing to Lingo

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — **use `uv`, not `pip`**. All dependency management goes through `uv sync` / `uv run`.
- Node.js 20+ (frontend only)
- Docker (integration tests and local Postgres)

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

Frontend (only needed if you change UI code):

```bash
cd frontend && npm install && npm run build
```

Build output goes to `src/lingo/static/` and is served by FastAPI.

## Running tests

**Unit tests** — no Docker required:

```bash
make test-unit
```

**Integration tests** — spins up a real Postgres container, creates `lingo_test`, runs Alembic migrations:

```bash
make test-integration
```

**All tests:**

```bash
make test
```

**Frontend tests:**

```bash
cd frontend && npm test
```

### Test approach

Follow red/green TDD: write a failing test first, then implement. PRs without tests for new behavior will be asked to add them before merge.

- Backend unit tests live in `tests/unit/` and must not require Docker.
- Backend integration tests live in `tests/integration/` and hit a real Postgres instance. Use the fixtures in `tests/integration/conftest.py` — do not add `asyncio_mode` overrides or mock the database.
- Frontend tests use Vitest + React Testing Library in `frontend/src/`.

## Making changes

### Backend

- Keep async throughout — all database calls go through SQLAlchemy async sessions.
- New database columns require an Alembic migration: `uv run alembic revision --autogenerate -m "describe the change"`. Review the generated migration before committing.
- The scheduler (`APScheduler`) runs in-process and requires `--workers 1` in production. Keep scheduled jobs stateless and idempotent.
- New API endpoints must require authentication. Do not add unauthenticated endpoints without a strong reason.

### Frontend

- Components live in `frontend/src/components/`. Data fetching goes through TanStack Query hooks in `frontend/src/hooks/useTerms.ts`.
- Run `npm run lint` before pushing — ESLint is strict on React hooks rules.
- After UI changes, run `npm run build` to regenerate `src/lingo/static/`. Commit the built output so the server has it.

### Migrations

Always write both `upgrade()` and `downgrade()` in migrations. Missing `downgrade()` that drops enum types causes "type already exists" errors on re-upgrade — see CHANGELOG for prior incident.

## Submitting a PR

1. Branch off `main`.
2. Keep PRs focused — one logical change per PR.
3. Update `CHANGELOG.md` under `## [Unreleased]` following the [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.
4. Ensure `make test` passes locally.

## Key gotchas

| Gotcha | Why it matters |
|--------|----------------|
| Use `uv run` for all Python commands | Ensures the managed virtualenv is used, not system Python |
| `LINGO_DEV_MODE=true` is dev-only | Never set this in production — it disables auth entirely |
| `--workers 1` in production | APScheduler runs in-process; multiple workers cause duplicate job execution |
| `asyncio_mode = "auto"` | Already set in `pyproject.toml` — don't add `@pytest.mark.asyncio` to every test |
| Rebuild frontend after UI changes | `src/lingo/static/` is served directly by FastAPI — stale builds cause confusing behavior |
