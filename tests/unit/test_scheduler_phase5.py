"""Tests for Phase 5: Background Jobs (APScheduler + Discovery + Staleness).

Strategy:
  - Job functions tested directly with in-memory SQLite + AsyncMock Slack client.
  - No real APScheduler instance needed — we just test the job logic itself.
  - Scheduler setup tested by verifying it exposes the right interface.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from lingo.models import Term, User
from lingo.models.base import Base
from lingo.models.job import Job, JobStatus, JobType

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
    """Seed: one owner, one official term (fresh), one stale term with owner."""
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

        # A fresh official term (confirmed recently)
        fresh = Term(
            name="API",
            full_name="Application Programming Interface",
            definition="A set of rules for building software.",
            status="official",
            source="user",
            owner_id=owner.id,
            last_confirmed_at=datetime.now(UTC),
        )
        # A stale official term (last confirmed 200 days ago)
        stale = Term(
            name="KPI",
            definition="Key Performance Indicator",
            status="official",
            source="user",
            owner_id=owner.id,
            last_confirmed_at=datetime.now(UTC) - timedelta(days=200),
        )
        # A pending term with no owner
        pending_no_owner = Term(
            name="PR",
            definition="Pull Request",
            status="pending",
            source="user",
        )
        sess.add_all([fresh, stale, pending_no_owner])
        await sess.commit()
        await sess.refresh(fresh)
        await sess.refresh(stale)
        await sess.refresh(pending_no_owner)

        return {
            "owner": owner,
            "fresh": fresh,
            "stale": stale,
            "pending_no_owner": pending_no_owner,
        }


# ---------------------------------------------------------------------------
# Scheduler setup
# ---------------------------------------------------------------------------


class TestSchedulerSetup:
    def test_scheduler_module_exposes_create_scheduler(self):
        """The scheduler module must export a create_scheduler function."""
        from lingo.scheduler.setup import create_scheduler

        assert callable(create_scheduler)

    def test_create_scheduler_returns_asyncio_scheduler(self):
        """create_scheduler() must return an APScheduler AsyncIOScheduler."""
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        from lingo.scheduler.setup import create_scheduler

        scheduler = create_scheduler(session_factory=MagicMock(), slack_client=MagicMock())
        assert isinstance(scheduler, AsyncIOScheduler)

    def test_scheduler_has_discovery_job(self):
        """The scheduler must include a discovery job."""
        from lingo.scheduler.setup import create_scheduler

        scheduler = create_scheduler(session_factory=MagicMock(), slack_client=MagicMock())
        job_ids = [job.id for job in scheduler.get_jobs()]
        assert any("discovery" in jid for jid in job_ids)

    def test_scheduler_has_staleness_job(self):
        """The scheduler must include a staleness job."""
        from lingo.scheduler.setup import create_scheduler

        scheduler = create_scheduler(session_factory=MagicMock(), slack_client=MagicMock())
        job_ids = [job.id for job in scheduler.get_jobs()]
        assert any("staleness" in jid for jid in job_ids)


# ---------------------------------------------------------------------------
# LingoStalenessJob
# ---------------------------------------------------------------------------


class TestLingoStalenessJob:
    async def test_flags_terms_beyond_threshold_as_stale(self, factory, seeded):
        """Terms whose last_confirmed_at is older than threshold must be marked is_stale."""
        from lingo.scheduler.jobs.staleness import run_staleness_job

        slack_client = AsyncMock()
        await run_staleness_job(
            session_factory=factory,
            slack_client=slack_client,
            stale_threshold_days=180,
        )

        async with factory() as sess:
            stale_term = await sess.get(Term, seeded["stale"].id)
            fresh_term = await sess.get(Term, seeded["fresh"].id)

        assert stale_term.is_stale is True
        assert fresh_term.is_stale is False

    async def test_sends_dm_to_owner_of_stale_term(self, factory, seeded):
        """Staleness job must DM the owner for each newly-stale term."""
        from lingo.scheduler.jobs.staleness import run_staleness_job

        slack_client = AsyncMock()
        await run_staleness_job(
            session_factory=factory,
            slack_client=slack_client,
            stale_threshold_days=180,
        )

        # Should have DM'd the owner at least once (for KPI)
        slack_client.chat_postMessage.assert_called()
        channels = [call.kwargs["channel"] for call in slack_client.chat_postMessage.call_args_list]
        assert seeded["owner"].slack_user_id in channels

    async def test_skips_terms_with_no_owner(self, factory, seeded):
        """Staleness job must NOT DM for terms with no owner."""
        from lingo.scheduler.jobs.staleness import run_staleness_job

        # Make pending_no_owner also old so it would be flagged
        async with factory() as sess:
            t = await sess.get(Term, seeded["pending_no_owner"].id)
            t.last_confirmed_at = datetime.now(UTC) - timedelta(days=200)
            await sess.commit()

        slack_client = AsyncMock()
        await run_staleness_job(
            session_factory=factory,
            slack_client=slack_client,
            stale_threshold_days=180,
        )

        # pending_no_owner has no owner → no DM for it
        # Only one DM (for KPI which has owner)
        assert slack_client.chat_postMessage.call_count == 1

    async def test_skips_already_stale_terms(self, factory, seeded):
        """If a term is already is_stale=True, the job should not DM again."""
        from lingo.scheduler.jobs.staleness import run_staleness_job

        # Pre-mark as stale
        async with factory() as sess:
            t = await sess.get(Term, seeded["stale"].id)
            t.is_stale = True
            await sess.commit()

        slack_client = AsyncMock()
        await run_staleness_job(
            session_factory=factory,
            slack_client=slack_client,
            stale_threshold_days=180,
        )

        # Already stale → no new DM
        slack_client.chat_postMessage.assert_not_called()

    async def test_records_job_in_db(self, factory, seeded):
        """Staleness job must create a Job row and mark it completed."""
        from lingo.scheduler.jobs.staleness import run_staleness_job

        slack_client = AsyncMock()
        await run_staleness_job(
            session_factory=factory,
            slack_client=slack_client,
            stale_threshold_days=180,
        )

        async with factory() as sess:
            result = await sess.execute(select(Job).where(Job.job_type == JobType.staleness))
            job = result.scalar_one_or_none()

        assert job is not None
        assert job.status == JobStatus.completed
        assert job.completed_at is not None

    async def test_job_marked_failed_on_error(self, factory, seeded):
        """If an error occurs mid-job, the Job row must be marked failed."""
        from lingo.scheduler.jobs.staleness import run_staleness_job

        slack_client = AsyncMock()
        # Force an error in the slack client
        slack_client.chat_postMessage.side_effect = RuntimeError("Slack API down")

        # Should not raise — errors are caught and recorded
        await run_staleness_job(
            session_factory=factory,
            slack_client=slack_client,
            stale_threshold_days=180,
        )

        async with factory() as sess:
            result = await sess.execute(select(Job).where(Job.job_type == JobType.staleness))
            job = result.scalar_one_or_none()

        assert job is not None
        assert job.status == JobStatus.failed
        assert job.error is not None


# ---------------------------------------------------------------------------
# LingoDiscoveryJob
# ---------------------------------------------------------------------------


class TestLingoDiscoveryJob:
    async def test_new_acronym_creates_suggested_term(self, factory, seeded):
        """An acronym found in Slack history that is unknown must be added as 'suggested'."""
        from lingo.scheduler.jobs.discovery import run_discovery_job

        # Simulate Slack returning a message with a new acronym
        slack_client = AsyncMock()
        slack_client.conversations_list.return_value = {
            "channels": [{"id": "C_GENERAL", "name": "general"}],
            "response_metadata": {"next_cursor": ""},
        }
        slack_client.conversations_history.return_value = {
            "messages": [
                {"text": "We need to update the SLO metrics ASAP.", "ts": "1234567890.000000"}
            ],
            "has_more": False,
        }

        await run_discovery_job(
            session_factory=factory,
            slack_client=slack_client,
            lookback_days=90,
        )

        async with factory() as sess:
            result = await sess.execute(select(Term).where(Term.name == "SLO"))
            term = result.scalar_one_or_none()

        assert term is not None
        assert term.status == "suggested"
        assert term.source == "slack_discovery"

    async def test_known_acronym_is_not_duplicated(self, factory, seeded):
        """An acronym already in the glossary must NOT be added again."""
        from lingo.scheduler.jobs.discovery import run_discovery_job

        slack_client = AsyncMock()
        slack_client.conversations_list.return_value = {
            "channels": [{"id": "C_GENERAL", "name": "general"}],
            "response_metadata": {"next_cursor": ""},
        }
        # "API" already exists in the seeded data
        slack_client.conversations_history.return_value = {
            "messages": [{"text": "Check the API docs.", "ts": "1234567890.000000"}],
            "has_more": False,
        }

        await run_discovery_job(
            session_factory=factory,
            slack_client=slack_client,
            lookback_days=90,
        )

        async with factory() as sess:
            result = await sess.execute(select(Term).where(Term.name == "API"))
            terms = result.scalars().all()

        # Must still be exactly one API term
        assert len(terms) == 1

    async def test_short_words_not_treated_as_acronyms(self, factory, seeded):
        """Single-letter tokens or words shorter than 2 chars must not be added."""
        from lingo.scheduler.jobs.discovery import run_discovery_job

        slack_client = AsyncMock()
        slack_client.conversations_list.return_value = {
            "channels": [{"id": "C_GENERAL", "name": "general"}],
            "response_metadata": {"next_cursor": ""},
        }
        slack_client.conversations_history.return_value = {
            "messages": [{"text": "I saw a X at the meeting.", "ts": "1234567890.000000"}],
            "has_more": False,
        }

        await run_discovery_job(
            session_factory=factory,
            slack_client=slack_client,
            lookback_days=90,
        )

        async with factory() as sess:
            result = await sess.execute(select(Term).where(Term.name == "X"))
            term = result.scalar_one_or_none()

        assert term is None

    async def test_stores_occurrence_count(self, factory, seeded):
        """occurrences_count must reflect how many times the acronym appeared."""
        from lingo.scheduler.jobs.discovery import run_discovery_job

        slack_client = AsyncMock()
        slack_client.conversations_list.return_value = {
            "channels": [{"id": "C_GENERAL", "name": "general"}],
            "response_metadata": {"next_cursor": ""},
        }
        slack_client.conversations_history.return_value = {
            "messages": [
                {"text": "OKR season is here.", "ts": "1234567890.000000"},
                {"text": "Set your OKR goals.", "ts": "1234567891.000000"},
                {"text": "OKR review next week.", "ts": "1234567892.000000"},
            ],
            "has_more": False,
        }

        await run_discovery_job(
            session_factory=factory,
            slack_client=slack_client,
            lookback_days=90,
        )

        async with factory() as sess:
            result = await sess.execute(select(Term).where(Term.name == "OKR"))
            term = result.scalar_one_or_none()

        assert term is not None
        assert term.occurrences_count == 3

    async def test_records_job_in_db(self, factory, seeded):
        """Discovery job must create a Job row and mark it completed."""
        from lingo.scheduler.jobs.discovery import run_discovery_job

        slack_client = AsyncMock()
        slack_client.conversations_list.return_value = {
            "channels": [],
            "response_metadata": {"next_cursor": ""},
        }

        await run_discovery_job(
            session_factory=factory,
            slack_client=slack_client,
            lookback_days=90,
        )

        async with factory() as sess:
            result = await sess.execute(select(Job).where(Job.job_type == JobType.discovery))
            job = result.scalar_one_or_none()

        assert job is not None
        assert job.status == JobStatus.completed

    async def test_stores_progress_json(self, factory, seeded):
        """Discovery job must persist progress_json with channels_scanned and terms_found."""
        from lingo.scheduler.jobs.discovery import run_discovery_job

        slack_client = AsyncMock()
        slack_client.conversations_list.return_value = {
            "channels": [{"id": "C_GENERAL", "name": "general"}],
            "response_metadata": {"next_cursor": ""},
        }
        slack_client.conversations_history.return_value = {
            "messages": [{"text": "We track MRR monthly.", "ts": "1234567890.000000"}],
            "has_more": False,
        }

        await run_discovery_job(
            session_factory=factory,
            slack_client=slack_client,
            lookback_days=90,
        )

        async with factory() as sess:
            result = await sess.execute(select(Job).where(Job.job_type == JobType.discovery))
            job = result.scalar_one_or_none()

        assert job.progress_json is not None
        assert "channels_scanned" in job.progress_json
        assert "terms_found" in job.progress_json

    async def test_job_marked_failed_on_error(self, factory, seeded):
        """If Slack API errors, Job row must be marked failed with error message."""
        from lingo.scheduler.jobs.discovery import run_discovery_job

        slack_client = AsyncMock()
        slack_client.conversations_list.side_effect = RuntimeError("Slack down")

        await run_discovery_job(
            session_factory=factory,
            slack_client=slack_client,
            lookback_days=90,
        )

        async with factory() as sess:
            result = await sess.execute(select(Job).where(Job.job_type == JobType.discovery))
            job = result.scalar_one_or_none()

        assert job is not None
        assert job.status == JobStatus.failed
        assert job.error is not None
