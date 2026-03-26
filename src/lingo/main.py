"""FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from lingo.api.routes import terms
from lingo.api.routes import export, users, tokens, admin
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


@app.get("/health", tags=["ops"])
async def health():
    return {"status": "ok"}


app.include_router(terms.router)
app.include_router(export.router)
app.include_router(users.router)
app.include_router(tokens.router)
app.include_router(admin.router)

# MCP endpoint — bearer token auth required
app.mount("/mcp", MCPBearerAuthMiddleware(_mcp_asgi))
