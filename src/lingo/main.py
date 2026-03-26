"""FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from lingo.api.routes import terms
from lingo.api.routes import export, users, tokens, admin
from lingo.mcp.app import mcp
from lingo.mcp.auth import MCPBearerAuthMiddleware

# Build the MCP ASGI app first so we can wire its lifespan into FastAPI
_mcp_asgi = mcp.http_app(path="/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Wrap FastMCP's lifespan so its session manager starts with the server."""
    async with _mcp_asgi.lifespan(app):
        yield


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
