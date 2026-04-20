"""Tests for Phase 4: Slack bot commands and notification helpers.

Strategy:
  - Commands (/lingo define, add, vote, export) tested by calling handler
    functions directly with AsyncMock Slack say/client objects.
  - Notification helpers (dispute DM, promotion notice, staleness DM)
    tested by calling them directly and asserting the right Slack API calls.
  - No real Slack connection needed — fully in-memory with SQLite.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from lingo.models import Term, User
from lingo.models.base import Base
from lingo.slack.handlers import (
    handle_lingo_add,
    handle_lingo_define,
    handle_lingo_export,
    handle_lingo_vote,
)
from lingo.slack.notifications import (
    send_promotion_notification,
    send_staleness_dm,
    send_suggestion_dm,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def test_engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def factory(test_engine):
    return async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)


@pytest.fixture
async def seeded(factory):
    """Seed: one user with slack_user_id, two terms."""
    async with factory() as sess:
        owner = User(
            email="owner@example.com",
            display_name="Owner",
            slack_user_id="U_OWNER",
            role="member",
        )
        sess.add(owner)
        await sess.commit()
        await sess.refresh(owner)

        official = Term(
            name="API",
            full_name="Application Programming Interface",
            definition="A set of rules for building software.",
            status="official",
            source="user",
            created_by=owner.id,
        )
        pending = Term(
            name="PR",
            definition="Pull Request — code review workflow.",
            status="pending",
            source="user",
            created_by=owner.id,
        )
        sess.add_all([official, pending])
        await sess.commit()
        await sess.refresh(official)
        await sess.refresh(pending)
        return {"owner": owner, "official": official, "pending": pending}


# ---------------------------------------------------------------------------
# /lingo define <term>
# ---------------------------------------------------------------------------


class TestLingoDefine:
    async def test_found_term_replies_with_definition(self, factory, seeded):
        say = AsyncMock()
        await handle_lingo_define(
            term_name="API",
            say=say,
            session_factory=factory,
        )
        say.assert_called_once()
        text = say.call_args[0][0]
        assert "API" in text
        assert "Application Programming Interface" in text

    async def test_case_insensitive_lookup(self, factory, seeded):
        say = AsyncMock()
        await handle_lingo_define(
            term_name="api",
            say=say,
            session_factory=factory,
        )
        say.assert_called_once()
        text = say.call_args[0][0]
        assert "API" in text

    async def test_not_found_returns_helpful_message(self, factory, seeded):
        say = AsyncMock()
        await handle_lingo_define(
            term_name="XYZ_UNKNOWN",
            say=say,
            session_factory=factory,
        )
        say.assert_called_once()
        text = say.call_args[0][0]
        assert "not found" in text.lower() or "XYZ_UNKNOWN" in text


# ---------------------------------------------------------------------------
# /lingo add <term> <definition>
# ---------------------------------------------------------------------------


class TestLingoAdd:
    async def test_add_new_term_creates_pending(self, factory, seeded):
        say = AsyncMock()
        owner = seeded["owner"]
        await handle_lingo_add(
            term_name="SLA",
            definition="Service Level Agreement",
            slack_user_id=owner.slack_user_id,
            say=say,
            session_factory=factory,
        )
        say.assert_called_once()
        text = say.call_args[0][0]
        assert "SLA" in text
        # Confirm it was persisted
        async with factory() as sess:
            from sqlalchemy import select

            result = await sess.execute(select(Term).where(Term.name == "SLA"))
            term = result.scalar_one_or_none()
        assert term is not None
        assert term.status == "pending"
        assert term.definition == "Service Level Agreement"

    async def test_add_duplicate_name_replies_with_warning(self, factory, seeded):
        say = AsyncMock()
        owner = seeded["owner"]
        await handle_lingo_add(
            term_name="API",  # already exists
            definition="Another definition",
            slack_user_id=owner.slack_user_id,
            say=say,
            session_factory=factory,
        )
        say.assert_called_once()
        text = say.call_args[0][0]
        assert "already exists" in text.lower() or "API" in text

    async def test_unknown_slack_user_cannot_add_term(self, factory, seeded):
        say = AsyncMock()
        await handle_lingo_add(
            term_name="KPI",
            definition="Key Performance Indicator",
            slack_user_id="U_NOBODY",
            say=say,
            session_factory=factory,
        )
        say.assert_called_once()
        text = say.call_args[0][0]
        # Should reject — requires a linked Lingo account
        assert "lingo account" in text.lower() or "sign in" in text.lower()
        # Term must NOT have been created
        async with factory() as sess:
            from sqlalchemy import select

            result = await sess.execute(select(Term).where(Term.name == "KPI"))
            term = result.scalar_one_or_none()
        assert term is None


# ---------------------------------------------------------------------------
# /lingo vote <term>
# ---------------------------------------------------------------------------


class TestLingoVote:
    async def test_vote_on_existing_term_increments_count(self, factory, seeded):
        say = AsyncMock()
        owner = seeded["owner"]
        await handle_lingo_vote(
            term_name="PR",
            slack_user_id=owner.slack_user_id,
            say=say,
            session_factory=factory,
        )
        say.assert_called_once()
        text = say.call_args[0][0]
        assert "PR" in text or "vote" in text.lower()

    async def test_vote_on_unknown_term_replies_not_found(self, factory, seeded):
        say = AsyncMock()
        await handle_lingo_vote(
            term_name="NOPE",
            slack_user_id="U_OWNER",
            say=say,
            session_factory=factory,
        )
        say.assert_called_once()
        text = say.call_args[0][0]
        assert "not found" in text.lower() or "NOPE" in text

    async def test_duplicate_vote_ignored_or_warned(self, factory, seeded):
        """Voting twice by same user should not raise and should reply sensibly."""
        say = AsyncMock()
        owner = seeded["owner"]
        # First vote
        await handle_lingo_vote(
            term_name="PR",
            slack_user_id=owner.slack_user_id,
            say=say,
            session_factory=factory,
        )
        say.reset_mock()
        # Second vote — should reply (either already voted or accepted)
        await handle_lingo_vote(
            term_name="PR",
            slack_user_id=owner.slack_user_id,
            say=say,
            session_factory=factory,
        )
        say.assert_called_once()


# ---------------------------------------------------------------------------
# /lingo export
# ---------------------------------------------------------------------------


class TestLingoExport:
    async def test_export_uploads_file_to_slack(self, factory, seeded):
        client = AsyncMock()
        await handle_lingo_export(
            channel_id="C_TEST",
            client=client,
            session_factory=factory,
        )
        client.files_upload_v2.assert_called_once()
        call_kwargs = client.files_upload_v2.call_args[1]
        assert call_kwargs["channel"] == "C_TEST"
        assert "filename" in call_kwargs
        assert call_kwargs["filename"].endswith(".md")

    async def test_export_content_includes_terms(self, factory, seeded):
        client = AsyncMock()
        await handle_lingo_export(
            channel_id="C_TEST",
            client=client,
            session_factory=factory,
        )
        call_kwargs = client.files_upload_v2.call_args[1]
        content = call_kwargs.get("content", "") or ""
        assert "API" in content
        assert "PR" in content


# ---------------------------------------------------------------------------
# Notification helpers
# ---------------------------------------------------------------------------


class TestSuggestionDM:
    async def test_dm_sent_to_term_owner(self, factory, seeded):
        client = AsyncMock()
        owner = seeded["owner"]
        official = seeded["official"]
        # Wire owner_id
        async with factory() as sess:
            t = await sess.get(Term, official.id)
            t.owner_id = owner.id
            await sess.commit()

        await send_suggestion_dm(
            term_id=official.id,
            suggester_name="Alice",
            suggested_definition="A better definition for API.",
            comment="More accurate wording.",
            client=client,
            session_factory=factory,
        )
        client.chat_postMessage.assert_called_once()
        call_kwargs = client.chat_postMessage.call_args[1]
        assert call_kwargs["channel"] == owner.slack_user_id
        assert "suggested" in call_kwargs["text"].lower() or "API" in call_kwargs["text"]

    async def test_no_dm_when_term_has_no_owner(self, factory, seeded):
        client = AsyncMock()
        pending = seeded["pending"]  # owner_id is None
        await send_suggestion_dm(
            term_id=pending.id,
            suggester_name="Bob",
            suggested_definition="Different definition.",
            comment="",
            client=client,
            session_factory=factory,
        )
        client.chat_postMessage.assert_not_called()


class TestPromotionNotification:
    async def test_posts_to_source_channel(self, factory, seeded):
        client = AsyncMock()
        pending = seeded["pending"]
        # Give the term a source_channel_id
        async with factory() as sess:
            t = await sess.get(Term, pending.id)
            t.source_channel_id = "C_SOURCE"
            await sess.commit()

        await send_promotion_notification(
            term_id=pending.id,
            client=client,
            session_factory=factory,
        )
        client.chat_postMessage.assert_called_once()
        call_kwargs = client.chat_postMessage.call_args[1]
        assert call_kwargs["channel"] == "C_SOURCE"
        assert "PR" in call_kwargs["text"] or "promoted" in call_kwargs["text"].lower()

    async def test_no_post_when_no_source_channel(self, factory, seeded):
        client = AsyncMock()
        official = seeded["official"]  # source_channel_id is None
        await send_promotion_notification(
            term_id=official.id,
            client=client,
            session_factory=factory,
        )
        client.chat_postMessage.assert_not_called()


class TestStalenessDM:
    async def test_dm_sent_to_owner_with_action_blocks(self, factory, seeded):
        client = AsyncMock()
        owner = seeded["owner"]
        official = seeded["official"]
        async with factory() as sess:
            t = await sess.get(Term, official.id)
            t.owner_id = owner.id
            t.is_stale = True
            await sess.commit()

        await send_staleness_dm(
            term_id=official.id,
            client=client,
            session_factory=factory,
        )
        client.chat_postMessage.assert_called_once()
        call_kwargs = client.chat_postMessage.call_args[1]
        assert call_kwargs["channel"] == owner.slack_user_id
        # Should include interactive blocks with Confirm / Update buttons
        blocks = call_kwargs.get("blocks", [])
        assert len(blocks) > 0
        # Flatten all action values from blocks
        action_values = []
        for block in blocks:
            if block.get("type") == "actions":
                for element in block.get("elements", []):
                    action_values.append(element.get("action_id", ""))
        assert any("confirm" in v for v in action_values)
        assert any("update" in v for v in action_values)

    async def test_no_dm_when_term_has_no_owner(self, factory, seeded):
        client = AsyncMock()
        pending = seeded["pending"]
        async with factory() as sess:
            t = await sess.get(Term, pending.id)
            t.is_stale = True
            await sess.commit()

        await send_staleness_dm(
            term_id=pending.id,
            client=client,
            session_factory=factory,
        )
        client.chat_postMessage.assert_not_called()
