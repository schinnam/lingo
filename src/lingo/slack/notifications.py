"""Slack notification helpers for Lingo events.

Each function takes an explicit session_factory for testability.
"""

from __future__ import annotations

from uuid import UUID

from lingo.models.term import Term
from lingo.models.user import User


async def send_dispute_dm(
    *,
    term_id: UUID,
    disputer_name: str,
    reason: str,
    client,
    session_factory,
) -> None:
    """DM the term owner when someone disputes a definition."""
    async with session_factory() as session:
        term = await session.get(Term, term_id)
        if term is None or term.owner_id is None:
            return

        owner = await session.get(User, term.owner_id)
        if owner is None or not owner.slack_user_id:
            return

    text = (
        f":warning: *{disputer_name}* has disputed the definition of *{term.name}*.\n"
        f">_{reason}_\n"
        f"Please review and update the definition if needed."
    )
    await client.chat_postMessage(channel=owner.slack_user_id, text=text)


async def send_promotion_notification(
    *,
    term_id: UUID,
    client,
    session_factory,
) -> None:
    """Post to the source channel when a term is promoted to community/official."""
    async with session_factory() as session:
        term = await session.get(Term, term_id)
        if term is None or not term.source_channel_id:
            return

    text = (
        f":tada: *{term.name}* has been promoted to *{term.status}* status in the Lingo glossary!"
    )
    await client.chat_postMessage(channel=term.source_channel_id, text=text)


async def send_staleness_dm(
    *,
    term_id: UUID,
    client,
    session_factory,
) -> None:
    """DM the term owner asking them to confirm or update a stale definition."""
    async with session_factory() as session:
        term = await session.get(Term, term_id)
        if term is None or term.owner_id is None:
            return

        owner = await session.get(User, term.owner_id)
        if owner is None or not owner.slack_user_id:
            return

    text = (
        f":hourglass: The definition of *{term.name}* may be out of date. "
        f"Please confirm it's still accurate or update it."
    )
    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": text},
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Confirm"},
                    "style": "primary",
                    "action_id": f"staleness_confirm_{term_id}",
                    "value": str(term_id),
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Update"},
                    "action_id": f"staleness_update_{term_id}",
                    "value": str(term_id),
                },
            ],
        },
    ]
    await client.chat_postMessage(
        channel=owner.slack_user_id,
        text=text,
        blocks=blocks,
    )
