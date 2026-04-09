"""Slack slash-command handlers for /lingo sub-commands.

Each handler is a plain async function that accepts a session_factory so it
can be tested in isolation without a real Slack connection.
"""
from __future__ import annotations

from typing import Callable

from sqlalchemy import select

from lingo.models.term import Term
from lingo.models.user import User
from lingo.services.term_service import TermService
from lingo.services.vote_service import AlreadyVotedError, VoteService

async def resolve_slack_user(slack_user_id: str, session) -> "User | None":
    """Look up a User by Slack user ID. Returns None if not linked."""
    result = await session.execute(
        select(User).where(User.slack_user_id == slack_user_id)
    )
    return result.scalar_one_or_none()


# Maximum number of terms fetched for an export to avoid memory exhaustion.
_EXPORT_LIMIT = 1000


async def handle_lingo_define(
    *,
    term_name: str,
    say: Callable,
    session_factory,
) -> None:
    """Look up a term by name and reply with its definition."""
    async with session_factory() as session:
        result = await session.execute(
            select(Term).where(Term.name.ilike(term_name))
        )
        term = result.scalar_one_or_none()

    if term is None:
        await say(f"Term '{term_name}' not found in the glossary.")
        return

    parts = [f"*{term.name}*"]
    if term.full_name:
        parts.append(f" ({term.full_name})")
    parts.append(f"\n{term.definition}")
    parts.append(f"\nStatus: _{term.status}_")
    await say("".join(parts))


async def handle_lingo_add(
    *,
    term_name: str,
    definition: str,
    slack_user_id: str,
    say: Callable,
    session_factory,
) -> None:
    """Add a new term to the glossary as pending.

    Requires the caller to have a Lingo account linked to their Slack user ID.
    """
    async with session_factory() as session:
        # Check for duplicate
        existing = (await session.execute(
            select(Term).where(Term.name.ilike(term_name))
        )).scalar_one_or_none()

        if existing is not None:
            await say(
                f"Term *{existing.name}* already exists in the glossary. "
                f"Use `/lingo define {existing.name}` to see it."
            )
            return

        # Require a linked Lingo account — anonymous term creation is not allowed.
        user = await resolve_slack_user(slack_user_id, session)

        if user is None:
            await say(
                "You need a Lingo account to add terms. "
                "Please sign in at your Lingo instance."
            )
            return

        svc = TermService(session)
        term = await svc.create(
            name=term_name,
            definition=definition,
            created_by=user.id,
            source="slack",
        )

    await say(
        f"Added *{term.name}* to the glossary. "
        f"It will be visible once approved. Status: _{term.status}_"
    )


async def handle_lingo_vote(
    *,
    term_name: str,
    slack_user_id: str,
    say: Callable,
    session_factory,
) -> None:
    """Cast a vote for a term."""
    async with session_factory() as session:
        term = (await session.execute(
            select(Term).where(Term.name.ilike(term_name))
        )).scalar_one_or_none()

        if term is None:
            await say(f"Term '{term_name}' not found in the glossary.")
            return

        # Resolve user
        user = await resolve_slack_user(slack_user_id, session)

        if user is None:
            await say(
                "You need a Lingo account to vote. "
                "Please sign in at your Lingo instance."
            )
            return

        svc = VoteService(session)
        try:
            result = await svc.vote(term_id=term.id, user_id=user.id)
            await say(
                f"Voted for *{term.name}*! Total votes: {result.vote_count}"
            )
        except AlreadyVotedError:
            await say(f"You have already voted for *{term.name}*.")


async def handle_lingo_export(
    *,
    channel_id: str,
    client,
    session_factory,
) -> None:
    """Export the glossary as a Markdown file and upload to Slack.

    Capped at _EXPORT_LIMIT terms to prevent memory exhaustion.
    """
    async with session_factory() as session:
        result = await session.execute(
            select(Term).order_by(Term.name).limit(_EXPORT_LIMIT)
        )
        terms = list(result.scalars().all())

    lines = ["# Lingo Glossary\n"]
    for term in terms:
        header = f"## {term.name}"
        if term.full_name:
            header += f" ({term.full_name})"
        lines.append(header)
        lines.append(f"**Status:** {term.status}")
        if term.category:
            lines.append(f"**Category:** {term.category}")
        lines.append(f"\n{term.definition}\n")

    content = "\n".join(lines)

    await client.files_upload_v2(
        channel=channel_id,
        filename="lingo-glossary.md",
        content=content,
        title="Lingo Glossary Export",
    )
