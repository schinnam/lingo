"""FastAPI application entry point."""
from fastapi import FastAPI

from lingo.api.routes import terms

app = FastAPI(
    title="Lingo",
    description="Self-hosted company glossary — Slack, CLI, and AI agents",
    version="0.1.0",
)


@app.get("/health", tags=["ops"])
async def health():
    return {"status": "ok"}


app.include_router(terms.router)
