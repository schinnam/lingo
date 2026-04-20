"""Slack events endpoint."""

from fastapi import APIRouter, Request
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler

from lingo.slack.app import slack_app

router = APIRouter(tags=["slack"])
handler = AsyncSlackRequestHandler(slack_app)


@router.post("/slack/events", include_in_schema=False)
async def slack_events(req: Request):
    """Handle Slack events via Bolt's FastAPI adapter."""
    return await handler.handle(req)
