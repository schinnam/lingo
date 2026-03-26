"""FastAPI application entry point."""
from fastapi import FastAPI

from lingo.api.routes import terms
from lingo.api.routes import export, users, tokens, admin

app = FastAPI(
    title="Lingo",
    description="Self-hosted company glossary — Slack, CLI, and AI agents",
    version="0.1.0",
)


@app.get("/health", tags=["ops"])
async def health():
    return {"status": "ok"}


app.include_router(terms.router)
app.include_router(export.router)
app.include_router(users.router)
app.include_router(tokens.router)
app.include_router(admin.router)
