# Installation

Lingo ships as a single Docker image containing the Python backend and the pre-built React frontend. The recommended approach is Docker Compose.

## Prerequisites

| Requirement | Minimum version | Notes |
|---|---|---|
| **Docker** | 20.10+ | Required for the database |
| **Docker Compose** | 2.0+ | Included with Docker Desktop |
| **PostgreSQL** | 14+ | Provided by the compose file; bring your own for production |

For local development without Docker (backend only):

| Requirement | Minimum version | Notes |
|---|---|---|
| **Python** | 3.12+ | |
| **uv** | latest | `brew install uv` on macOS, or see [docs.astral.sh/uv](https://docs.astral.sh/uv/) |
| **Node.js** | 20+ | Only needed to rebuild the frontend |

---

## Option 1 — Docker Compose (recommended)

Clone the repository and start everything with one command:

```bash
git clone https://github.com/schinnam/lingo
cd lingo
docker compose up
```

This starts:

- **PostgreSQL 16** on port 5432 (internal only)
- **Lingo** on `http://localhost:8000` with `LINGO_DEV_MODE=true`

Dev mode is on by default in the compose file so you can explore without configuring OIDC. **Never use dev mode in production.**

---

## Option 2 — Local development

Use this when you want to iterate on the backend with hot-reload.

### 1. Start a database

```bash
docker compose up postgres -d
```

Or point `LINGO_DATABASE_URL` at any running Postgres instance.

### 2. Install Python dependencies

```bash
uv sync
```

### 3. Run database migrations

```bash
LINGO_DEV_MODE=true uv run alembic upgrade head
```

### 4. Start the server

```bash
LINGO_DEV_MODE=true uv run uvicorn lingo.main:app --reload
```

The server is at `http://localhost:8000`. Interactive API docs at `http://localhost:8000/docs`.

### 5. Rebuild the frontend (optional)

The repository ships a pre-built frontend in `src/lingo/static/`. To rebuild after making UI changes:

```bash
cd frontend
npm install
npm run build
```

---

## Install the CLI

After setting up the server, install the `lingo` command-line tool:

```bash
uv pip install -e .
```

This installs into the project virtualenv. Run commands via `uv run lingo` from the repo directory:

```bash
uv run lingo --help
```

To make `lingo` available as a bare command anywhere in your shell, install it as a global tool instead:

```bash
uv tool install .
lingo --help
```

See the [CLI guide](../usage/cli.md) for usage.

---

## Next steps

- [Quickstart](quickstart.md) — add your first term
- [Configuration](configuration.md) — environment variables reference
