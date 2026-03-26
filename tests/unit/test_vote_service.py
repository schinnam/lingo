"""Tests for voting mechanics and status auto-transitions."""
import pytest

from lingo.models import Vote
from lingo.services.term_service import TermService
from lingo.services.vote_service import (
    VoteService,
    AlreadyVotedError,
    StatusTransition,
)


class TestCastVote:
    async def test_vote_increments_count(self, session, member_user):
        term_svc = TermService(session)
        vote_svc = VoteService(session, community_threshold=3, official_threshold=10)

        term = await term_svc.create(
            name="TDD", definition="Test Driven Development", created_by=member_user.id
        )
        result = await vote_svc.vote(term_id=term.id, user_id=member_user.id)
        assert result.vote_count == 1

    async def test_duplicate_vote_raises(self, session, member_user):
        term_svc = TermService(session)
        vote_svc = VoteService(session, community_threshold=3, official_threshold=10)

        term = await term_svc.create(
            name="PR", definition="Pull Request", created_by=member_user.id
        )
        await vote_svc.vote(term_id=term.id, user_id=member_user.id)

        with pytest.raises(AlreadyVotedError):
            await vote_svc.vote(term_id=term.id, user_id=member_user.id)

    async def test_vote_persisted_in_db(self, session, member_user):
        from sqlalchemy import select
        term_svc = TermService(session)
        vote_svc = VoteService(session, community_threshold=3, official_threshold=10)

        term = await term_svc.create(
            name="CI", definition="Continuous Integration", created_by=member_user.id
        )
        await vote_svc.vote(term_id=term.id, user_id=member_user.id)

        row = (await session.execute(
            select(Vote).where(Vote.term_id == term.id, Vote.user_id == member_user.id)
        )).scalar_one_or_none()
        assert row is not None


class TestStatusTransitions:
    async def _make_users(self, session, n: int):
        """Create n distinct users."""
        from lingo.models import User
        users = []
        for i in range(n):
            u = User(email=f"voter{i}@example.com", display_name=f"Voter {i}")
            session.add(u)
            users.append(u)
        await session.commit()
        for u in users:
            await session.refresh(u)
        return users

    async def test_pending_to_community_at_threshold(self, session, member_user):
        term_svc = TermService(session)
        vote_svc = VoteService(session, community_threshold=3, official_threshold=10)

        term = await term_svc.create(
            name="MVP", definition="Minimum Viable Product", created_by=member_user.id
        )
        assert term.status == "pending"

        voters = await self._make_users(session, 3)
        result = None
        for voter in voters:
            result = await vote_svc.vote(term_id=term.id, user_id=voter.id)

        assert result.transition == StatusTransition.to_community
        refreshed = await term_svc.get(term.id)
        assert refreshed.status == "community"

    async def test_community_to_official_at_threshold(self, session, member_user):
        term_svc = TermService(session)
        vote_svc = VoteService(session, community_threshold=3, official_threshold=10)

        term = await term_svc.create(
            name="SLA", definition="Service Level Agreement", created_by=member_user.id
        )
        voters = await self._make_users(session, 10)
        result = None
        for voter in voters:
            result = await vote_svc.vote(term_id=term.id, user_id=voter.id)

        assert result.transition == StatusTransition.to_official
        refreshed = await term_svc.get(term.id)
        assert refreshed.status == "official"

    async def test_no_transition_below_threshold(self, session, member_user):
        term_svc = TermService(session)
        vote_svc = VoteService(session, community_threshold=3, official_threshold=10)

        term = await term_svc.create(
            name="ETA", definition="Estimated Time of Arrival", created_by=member_user.id
        )
        voters = await self._make_users(session, 2)
        result = None
        for voter in voters:
            result = await vote_svc.vote(term_id=term.id, user_id=voter.id)

        assert result.transition is None
        refreshed = await term_svc.get(term.id)
        assert refreshed.status == "pending"

    async def test_votes_not_reversed_on_status_change(self, session, member_user):
        """Vote count is preserved; demotion doesn't reset votes."""
        from sqlalchemy import select, func as sqlfunc
        term_svc = TermService(session)
        vote_svc = VoteService(session, community_threshold=3, official_threshold=10)

        term = await term_svc.create(
            name="OKR", definition="Objectives and Key Results", created_by=member_user.id
        )
        voters = await self._make_users(session, 3)
        for voter in voters:
            await vote_svc.vote(term_id=term.id, user_id=voter.id)

        # Manually demote back to pending (editor action)
        refreshed = await term_svc.get(term.id)
        refreshed.status = "pending"
        await session.commit()

        vote_count = (await session.execute(
            select(sqlfunc.count()).select_from(Vote).where(Vote.term_id == term.id)
        )).scalar()
        assert vote_count == 3


class TestEditorMarkOfficial:
    async def test_editor_can_mark_official_directly(self, session, member_user, admin_user):
        term_svc = TermService(session)
        vote_svc = VoteService(session, community_threshold=3, official_threshold=10)

        term = await term_svc.create(
            name="RFC", definition="Request for Comments", created_by=member_user.id
        )
        # editor fast-tracks to official (0 votes needed)
        updated = await vote_svc.mark_official(term_id=term.id, editor_id=admin_user.id)
        assert updated.status == "official"
