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

Server: `http://localhost:8000` — `LINGO_DEV_MODE=true` disables Slack auth so you can test locally. Log in via `http://localhost:8000/auth/dev/login?email=you@example.com` instead of going through Slack.

**Frontend development** — two modes:

```bash
# Fast iteration with HMR (Vite dev server, NOT served by FastAPI)
cd frontend && npm install && npm run dev

# Full-stack / production-parity (FastAPI serves the built output)
cd frontend && npm run build
# Build output goes to src/lingo/static/ — commit this if you changed the UI
```

If you test via `http://localhost:8000` without rebuilding, you'll see stale output.

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

- Backend unit tests live in `tests/unit/` and use an in-memory SQLite database — no Docker required, fast.
- Backend integration tests live in `tests/integration/` and hit a real Postgres instance. Use the fixtures in `tests/integration/conftest.py` — do not mock the database or add `asyncio_mode` overrides.
- `tests/conftest.py` sets `LINGO_DEV_MODE=true` automatically — you do not need to set it manually when running tests. `X-User-Id` auth in test clients works because of this; it is not free in production.
- Frontend tests use Vitest + React Testing Library in `frontend/src/`.

## Making changes

### Backend

- Keep async throughout — all database calls go through SQLAlchemy async sessions.
- New database columns require an Alembic migration: `uv run alembic revision --autogenerate -m "describe the change"`. Always review the generated file before committing — autogenerate misses check constraints and PostgreSQL-specific types.
- The scheduler (`APScheduler`) runs in-process and requires `--workers 1` in production. Keep scheduled jobs stateless and idempotent.
- New API endpoints must require authentication. Do not add unauthenticated endpoints without a strong reason.

### Frontend

- Components live in `frontend/src/components/`. Data fetching goes through TanStack Query hooks in `frontend/src/hooks/useTerms.ts`.
- Run `npm run lint` before pushing — ESLint is strict on React hooks rules.
- After UI changes, run `npm run build` to regenerate `src/lingo/static/`. Commit the built output so the server has it.

### Migrations

Always write both `upgrade()` and `downgrade()` in migrations. Missing `downgrade()` that drops enum types causes "type already exists" errors on re-upgrade — see CHANGELOG for prior incident.

## Releasing a New Version

Lingo exposes multiple versioned surfaces — the REST API (`/api/v1/`), Slack command syntax, and MCP tool definitions. A breaking change to any of them warrants a major version bump.

### Semantic Versioning policy

| Change | Version Bump |
|--------|-------------|
| Breaking change to `/api/v1/` response schema | MAJOR |
| Breaking change to Slack command syntax | MAJOR |
| Breaking change to MCP tool definitions | MAJOR |
| New API endpoint, Slack command, or MCP tool | MINOR |
| New config option (backwards-compatible) | MINOR |
| Bug fix, dependency update, docs | PATCH |

### Release steps

1. Update `version` in `pyproject.toml`
2. Update `CHANGELOG.md` — move Unreleased items under the new version heading with today's date
3. Commit: `git commit -m "chore: release vX.Y.Z"`
4. Tag: `git tag vX.Y.Z`
5. Push tag: `git push origin vX.Y.Z`
6. Create a GitHub Release from the tag — paste the CHANGELOG section as release notes
   The Docker image will be published automatically (see workflow #73)

## Submitting a PR

1. Branch off `main`.
2. Keep PRs focused — one logical change per PR.
3. Update `CHANGELOG.md` under `## [Unreleased]` following the [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.
4. Ensure `make test` passes locally.

## Key gotchas

| Gotcha | Why it matters |
|--------|----------------|
| Use `uv run` for all Python commands | Ensures the managed virtualenv is used, not system Python |
| `lingo` CLI not on PATH after `uv pip install -e .` | `uv pip install` installs into the project venv, not your global shell. Use `uv run lingo` or `uv tool install .` |
| `lingo export` shows empty output | Default status filter is `official`. Use `--status pending` to see terms that haven't been promoted yet. |
| `LINGO_DEV_MODE=true` is dev-only | Never set this in production — it disables auth entirely |
| `--workers 1` in production | APScheduler runs in-process; multiple workers cause duplicate job execution |
| `asyncio_mode = "auto"` | Already set in `pyproject.toml` — don't add `@pytest.mark.asyncio` to every test |
| Rebuild frontend after UI changes | `src/lingo/static/` is served directly by FastAPI — stale builds cause confusing behavior |
