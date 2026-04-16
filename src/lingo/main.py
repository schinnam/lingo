"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from lingo.api.routes import admin, auth, export, features, terms, tokens, users
from lingo.config import settings
from lingo.db.session import SessionFactory
from lingo.mcp.app import mcp
from lingo.mcp.auth import MCPBearerAuthMiddleware
from lingo.scheduler.setup import create_scheduler

# Build the MCP ASGI app first so we can wire its lifespan into FastAPI
_mcp_asgi = mcp.http_app(path="/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Wrap FastMCP's lifespan so its session manager starts with the server."""
    # Build Slack client only if tokens are configured
    slack_client = None
    if settings.slack_bot_token:
        from slack_sdk.web.async_client import AsyncWebClient

        slack_client = AsyncWebClient(token=settings.slack_bot_token)
    app.state.slack_client = slack_client

    scheduler = create_scheduler(
        session_factory=SessionFactory,
        slack_client=slack_client,
    )
    scheduler.start()

    async with _mcp_asgi.lifespan(app):
        yield

    scheduler.shutdown(wait=False)


app = FastAPI(
    title="Lingo",
    description="Self-hosted company glossary — Slack, CLI, and AI agents",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    max_age=86400,
    https_only=not settings.dev_mode,
    same_site="lax",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["ops"])
async def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(terms.router)
app.include_router(export.router)
app.include_router(users.router)
app.include_router(tokens.router)
app.include_router(admin.router)
app.include_router(features.router)

# MCP endpoint — bearer token auth required
app.mount("/mcp", MCPBearerAuthMiddleware(_mcp_asgi))

# SPA static files — served last so API routes take priority
_static_dir = Path(__file__).parent / "static"
if _static_dir.exists() and any(_static_dir.iterdir()):
    app.mount("/assets", StaticFiles(directory=_static_dir / "assets"), name="assets")

    _index = _static_dir / "index.html"
    _index_html: str | None = _index.read_text() if _index.exists() else None
    if _index_html and settings.dev_mode:
        _index_html = _index_html.replace(
            "<!-- lingo:dev-meta -->",
            '<meta name="lingo-dev-mode" content="true">',
        )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):  # noqa: ARG001
        if _index_html is None:
            return {"detail": "Frontend not built. Run `npm run build` in the frontend/ directory."}
        return HTMLResponse(content=_index_html)
