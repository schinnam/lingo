"""Slack AsyncApp (HTTP Events) for Lingo.

Commands:
  /lingo <term>                    — quick look up (shorthand for define)
  /lingo define <term>
  /lingo add <term> -- <definition>
  /lingo vote <term>
  /lingo export
  /lingo token [name]

Interactive actions:
  staleness_confirm_<term_id>
  staleness_update_<term_id>

Start with:
  LINGO_SLACK_BOT_TOKEN=... LINGO_SLACK_SIGNING_SECRET=... \\
  uv run python -m lingo.slack.app
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import UUID

from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient

from lingo.config import settings
from lingo.db.session import SessionFactory
from lingo.models.term import Term
from lingo.slack.handlers import (
    handle_lingo_add,
    handle_lingo_define,
    handle_lingo_export,
    handle_lingo_token,
    handle_lingo_vote,
)

# Use a shared AsyncWebClient to ensure connection pooling via aiohttp
slack_client = AsyncWebClient(
    token=settings.slack_bot_token,
    timeout=10,  # 10s timeout for outgoing calls to Slack API
)

slack_app = AsyncApp(
    client=slack_client,
    signing_secret=settings.slack_signing_secret or None,
    request_verification_enabled=not settings.dev_mode,
)


_COMMANDS = frozenset({"define", "add", "vote", "export", "token", "help"})

_HELP_TEXT = (
    "*Lingo commands:*\n"
    "• `/lingo <term>` — quick look up (shorthand for define)\n"
    "• `/lingo define <term>` — look up a term\n"
    "• `/lingo add <term> -- <definition>` — add a new term\n"
    "• `/lingo vote <term>` — vote for a term\n"
    "• `/lingo export` — download the full glossary\n"
    "• `/lingo token [name]` — generate an API token for CLI/MCP use"
)


@slack_app.command("/lingo")
async def lingo_command(ack, command, say, client):
    await ack()
    text = (command.get("text") or "").strip()
    channel_id = command.get("channel_id", "")
    slack_user_id = command.get("user_id", "")

    parts = text.split(None, 1)
    first_word = parts[0].lower() if parts else ""
    rest = parts[1].strip() if len(parts) > 1 else ""

    if not text or first_word == "help":
        await say(_HELP_TEXT)

    elif first_word not in _COMMANDS:
        # Treat entire text as a term name — shorthand for define
        await handle_lingo_define(
            term_name=text,
            say=say,
            session_factory=SessionFactory,
        )

    elif first_word == "define":
        if not rest:
            await say("Usage: `/lingo define <term>`\nExample: `/lingo define SLA`")
            return
        await handle_lingo_define(
            term_name=rest,
            say=say,
            session_factory=SessionFactory,
        )

    elif first_word == "add":
        if not rest:
            await say(
                "Usage: `/lingo add <term> -- <definition>`\n"
                "Example: `/lingo add SLA -- Service Level Agreement`"
            )
            return
        if " -- " in rest:
            term_name, definition = rest.split(" -- ", 1)
        else:
            sub_parts = rest.split(None, 1)
            if len(sub_parts) < 2:
                await say(
                    "Usage: `/lingo add <term> -- <definition>`\n"
                    "Example: `/lingo add SLA -- Service Level Agreement`"
                )
                return
            term_name, definition = sub_parts
        await handle_lingo_add(
            term_name=term_name.strip(),
            definition=definition.strip(),
            slack_user_id=slack_user_id,
            say=say,
            session_factory=SessionFactory,
        )

    elif first_word == "vote":
        if not rest:
            await say("Usage: `/lingo vote <term>`\nExample: `/lingo vote SLA`")
            return
        await handle_lingo_vote(
            term_name=rest,
            slack_user_id=slack_user_id,
            say=say,
            session_factory=SessionFactory,
        )

    elif first_word == "export":
        await handle_lingo_export(
            channel_id=channel_id,
            client=client,
            session_factory=SessionFactory,
        )

    elif first_word == "token":
        token_name = rest if rest else "Slack CLI token"
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
        term.last_confirmed_at = datetime.now(UTC)
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
        text=(f"To update *{term_name}*, use:\n`/lingo add {term_name} -- <new definition>`"),
    )
