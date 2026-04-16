"""Voting mechanics and status auto-transition service."""

import enum
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from lingo.models.term import Term
from lingo.models.vote import Vote
from lingo.services.term_service import TermNotFoundError


class AlreadyVotedError(Exception):
    pass


class StatusTransition(enum.StrEnum):
    to_community = "to_community"
    to_official = "to_official"


@dataclass
class VoteResult:
    vote_count: int
    transition: StatusTransition | None


class VoteService:
    def __init__(
        self,
        session: AsyncSession,
        community_threshold: int = 3,
        official_threshold: int = 10,
    ):
        self._session = session
        self._community_threshold = community_threshold
        self._official_threshold = official_threshold

    async def vote(self, *, term_id: UUID, user_id: UUID) -> VoteResult:
        term = await self._session.get(Term, term_id)
        if term is None:
            raise TermNotFoundError(f"Term {term_id} not found")

        # Check duplicate
        existing = (
            await self._session.execute(
                select(Vote).where(Vote.term_id == term_id, Vote.user_id == user_id)
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise AlreadyVotedError(f"User {user_id} already voted on term {term_id}")

        vote = Vote(term_id=term_id, user_id=user_id)
        self._session.add(vote)

        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            raise AlreadyVotedError(f"User {user_id} already voted on term {term_id}")

        # Count votes inside the same transaction — flush ensures our vote is visible
        vote_count = (
            await self._session.execute(
                select(func.count()).select_from(Vote).where(Vote.term_id == term_id)
            )
        ).scalar()

        # CAS status transition: atomic UPDATE ... WHERE status=<expected> AND version=<seen>
        # If another concurrent session already transitioned, rowcount == 0 and we skip.
        transition = None
        snapshot_status = term.status
        snapshot_version = term.version

        if snapshot_status == "community" and vote_count >= self._official_threshold:
            new_status = "official"
            desired_transition = StatusTransition.to_official
        elif snapshot_status == "pending" and vote_count >= self._community_threshold:
            new_status = "community"
            desired_transition = StatusTransition.to_community
        else:
            new_status = None
            desired_transition = None

        if new_status is not None:
            result = await self._session.execute(
                update(Term)
                .where(
                    Term.id == term_id,
                    Term.status == snapshot_status,
                    Term.version == snapshot_version,
                )
                .values(status=new_status, version=snapshot_version + 1)
            )
            if result.rowcount == 1:
                # We won the CAS — update the in-memory object to stay consistent
                term.status = new_status
                term.version = snapshot_version + 1
                transition = desired_transition

        await self._session.commit()
        return VoteResult(vote_count=vote_count, transition=transition)

    async def mark_official(self, *, term_id: UUID, editor_id: UUID) -> Term:
        term = await self._session.get(Term, term_id)
        if term is None:
            raise TermNotFoundError(f"Term {term_id} not found")
        term.status = "official"
        await self._session.commit()
        await self._session.refresh(term)
        return term
