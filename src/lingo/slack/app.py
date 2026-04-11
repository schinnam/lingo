"""Slack AsyncApp (Socket Mode) for Lingo.

Commands:
  /lingo define <term>
  /lingo add <term> -- <definition>
  /lingo vote <term>
  /lingo export
  /lingo token [name]

Interactive actions:
  staleness_confirm_<term_id>
  staleness_update_<term_id>

Start with:
  LINGO_SLACK_BOT_TOKEN=... LINGO_SLACK_APP_TOKEN=... LINGO_SLACK_SIGNING_SECRET=... \\
  uv run python -m lingo.slack.app
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import UUID

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from lingo.config import settings
from lingo.db.session import SessionFactory
from lingo.models.term import Term
from lingo.slack.handlers import (
    handle_lingo_define,
    handle_lingo_add,
    handle_lingo_vote,
    handle_lingo_export,
    handle_lingo_token,
)

slack_app = AsyncApp(
    token=settings.slack_bot_token,
    signing_secret=settings.slack_signing_secret or None,
)


@slack_app.command("/lingo")
async def lingo_command(ack, command, say, client):
    await ack()
    text = (command.get("text") or "").strip()
    channel_id = command.get("channel_id", "")
    slack_user_id = command.get("user_id", "")

    if text.startswith("define "):
        term_name = text[len("define "):].strip()
        await handle_lingo_define(
            term_name=term_name,
            say=say,
            session_factory=SessionFactory,
        )

    elif text.startswith("add "):
        # Format: add <term> -- <definition>
        remainder = text[len("add "):].strip()
        if " -- " in remainder:
            term_name, definition = remainder.split(" -- ", 1)
        else:
            parts = remainder.split(None, 1)
            if len(parts) < 2:
                await say(
                    "Usage: `/lingo add <term> -- <definition>`\n"
                    "Example: `/lingo add SLA -- Service Level Agreement`"
                )
                return
            term_name, definition = parts

        await handle_lingo_add(
            term_name=term_name.strip(),
            definition=definition.strip(),
            slack_user_id=slack_user_id,
            say=say,
            session_factory=SessionFactory,
        )

    elif text.startswith("vote "):
        term_name = text[len("vote "):].strip()
        await handle_lingo_vote(
            term_name=term_name,
            slack_user_id=slack_user_id,
            say=say,
            session_factory=SessionFactory,
        )

    elif text == "export":
        await handle_lingo_export(
            channel_id=channel_id,
            client=client,
            session_factory=SessionFactory,
        )

    elif text == "token" or text.startswith("token "):
        remainder = text[len("token"):].strip()
        token_name = remainder if remainder else "Slack CLI token"
        raw, error = await handle_lingo_token(
            slack_user_id=slack_user_id,
            name=token_name,
            session_factory=SessionFactory,
        )
        if error:
            await client.chat_postEphemeral(
                channel=channel_id,
                user=slack_user_id,
                text=f":x: {error}",
            )
        else:
            await client.chat_postEphemeral(
                channel=channel_id,
                user=slack_user_id,
                text=(
                    ":key: *Your new Lingo API token* (shown once — save it now):\n"
                    f"```{raw}```\n"
                    "*CLI usage:*\n"
                    f"`export LINGO_API_TOKEN={raw}`\n"
                    "*MCP usage:* set `LINGO_API_TOKEN` in your MCP server environment."
                ),
            )

    else:
        await say(
            "*Lingo commands:*\n"
            "• `/lingo define <term>` — look up a term\n"
            "• `/lingo add <term> -- <definition>` — add a new term\n"
            "• `/lingo vote <term>` — vote for a term\n"
            "• `/lingo export` — download the full glossary\n"
            "• `/lingo token [name]` — generate an API token for CLI/MCP use"
        )


@slack_app.action(re.compile(r"^staleness_confirm_.+"))
async def staleness_confirm(ack, action, body, client):
    """User clicked Confirm on a staleness DM."""
    await ack()
    raw_id = action.get("value") or ""
    slack_user_id = body.get("user", {}).get("id", "")

    try:
        term_uuid = UUID(raw_id)
    except ValueError:
        return

    async with SessionFactory() as session:
        term = await session.get(Term, term_uuid)
        if term is None:
            return
        term.last_confirmed_at = datetime.now(timezone.utc)
        term.is_stale = False
        await session.commit()
        term_name = term.name

    await client.chat_postMessage(
        channel=slack_user_id,
        text=f":white_check_mark: Thanks! *{term_name}* has been confirmed as up to date.",
    )


@slack_app.action(re.compile(r"^staleness_update_.+"))
async def staleness_update(ack, action, body, client):
    """User clicked Update on a staleness DM — prompt them via DM."""
    await ack()
    raw_id = action.get("value") or ""
    slack_user_id = body.get("user", {}).get("id", "")

    try:
        term_uuid = UUID(raw_id)
    except ValueError:
        return

    async with SessionFactory() as session:
        term = await session.get(Term, term_uuid)
        if term is None:
            return
        term_name = term.name

    await client.chat_postMessage(
        channel=slack_user_id,
        text=(
            f"To update *{term_name}*, use:\n"
            f"`/lingo add {term_name} -- <new definition>`"
        ),
    )


async def start():
    handler = AsyncSocketModeHandler(slack_app, settings.slack_app_token)
    await handler.start_async()


if __name__ == "__main__":
    import asyncio
    asyncio.run(start())
