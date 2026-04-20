"""Term CRUD service layer."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lingo.models.term import Term
from lingo.models.term_history import TermHistory
from lingo.models.term_relationship import TermRelationship
from lingo.services.profanity_service import ProfanityError, check_content

__all__ = [
    "AlreadyOwnedError",
    "InvalidStatusTransitionError",
    "ProfanityError",
    "RelationshipNotFoundError",
    "TermNotFoundError",
    "TermService",
    "VersionConflictError",
]


class TermNotFoundError(Exception):
    pass


class VersionConflictError(Exception):
    pass


class AlreadyOwnedError(Exception):
    pass


class RelationshipNotFoundError(Exception):
    pass


class InvalidStatusTransitionError(Exception):
    pass


class TermService:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        *,
        name: str,
        definition: str,
        created_by: UUID,
        full_name: str | None = None,
        category: str | None = None,
        source: str = "user",
    ) -> Term:
        await check_content(name=name, definition=definition)
        term = Term(
            name=name,
            definition=definition,
            full_name=full_name,
            category=category,
            status="pending",
            source=source,
            created_by=created_by,
        )
        self._session.add(term)
        await self._session.commit()
        await self._session.refresh(term)
        return term

    async def get(self, term_id: UUID) -> Term:
        term = await self._session.get(Term, term_id)
        if term is None:
            raise TermNotFoundError(f"Term {term_id} not found")
        return term

    async def list(
        self,
        *,
        q: str | None = None,
        status: str | None = None,
        category: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Term]:
        stmt = select(Term)
        if status is not None:
            stmt = stmt.where(Term.status == status)
        if category is not None:
            stmt = stmt.where(Term.category == category)
        if q is not None:
            pattern = f"%{q}%"
            stmt = stmt.where(
                Term.name.ilike(pattern)
                | Term.definition.ilike(pattern)
                | Term.full_name.ilike(pattern)
            )
        stmt = stmt.offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self,
        *,
        term_id: UUID,
        version: int,
        updated_by: UUID,
        definition: str | None = None,
        full_name: str | None = None,
        category: str | None = None,
        change_note: str | None = None,
    ) -> Term:
        term = await self._session.get(Term, term_id)
        if term is None:
            raise TermNotFoundError(f"Term {term_id} not found")
        if term.version != version:
            raise VersionConflictError(f"Version conflict: expected {term.version}, got {version}")

        # Snapshot history before mutation
        snapshot = TermHistory(
            term_id=term.id,
            definition=term.definition,
            full_name=term.full_name,
            category=term.category,
            owner_id=term.owner_id,
            status=term.status,
            changed_by=updated_by,
            change_note=change_note,
        )
        self._session.add(snapshot)

        if definition is not None:
            term.definition = definition
        if full_name is not None:
            term.full_name = full_name
        if category is not None:
            term.category = category
        term.version += 1

        await self._session.commit()
        await self._session.refresh(term)
        return term

    async def delete(self, term_id: UUID) -> None:
        term = await self._session.get(Term, term_id)
        if term is None:
            raise TermNotFoundError(f"Term {term_id} not found")
        await self._session.delete(term)
        await self._session.commit()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def mark_official(self, term_id: UUID, by_user: UUID) -> Term:
        term = await self._session.get(Term, term_id)
        if term is None:
            raise TermNotFoundError(f"Term {term_id} not found")
        snapshot = TermHistory(
            term_id=term.id,
            definition=term.definition,
            full_name=term.full_name,
            category=term.category,
            owner_id=term.owner_id,
            status=term.status,
            changed_by=by_user,
            change_note="Marked official by editor",
        )
        self._session.add(snapshot)
        term.status = "official"
        term.version += 1
        await self._session.commit()
        await self._session.refresh(term)
        return term

    async def confirm(self, term_id: UUID, by_user: UUID) -> Term:
        term = await self._session.get(Term, term_id)
        if term is None:
            raise TermNotFoundError(f"Term {term_id} not found")
        term.is_stale = False
        term.last_confirmed_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(term)
        return term

    async def dispute(self, term_id: UUID, by_user: UUID, comment: str = "") -> Term:
        term = await self._session.get(Term, term_id)
        if term is None:
            raise TermNotFoundError(f"Term {term_id} not found")
        change_note = f"Disputed: {comment}" if comment else "Disputed by user"
        snapshot = TermHistory(
            term_id=term.id,
            definition=term.definition,
            full_name=term.full_name,
            category=term.category,
            owner_id=term.owner_id,
            status=term.status,
            changed_by=by_user,
            change_note=change_note,
        )
        self._session.add(snapshot)
        term.is_disputed = True
        await self._session.commit()
        await self._session.refresh(term)
        return term

    async def claim(self, term_id: UUID, user_id: UUID, force: bool = False) -> Term:
        term = await self._session.get(Term, term_id)
        if term is None:
            raise TermNotFoundError(f"Term {term_id} not found")
        if term.owner_id is not None and not force:
            raise AlreadyOwnedError(f"Term {term_id} already has an owner")
        term.owner_id = user_id
        term.owned_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(term)
        return term

    async def promote(self, term_id: UUID, by_user: UUID) -> Term:
        """Promote a suggested term to pending."""
        term = await self._session.get(Term, term_id)
        if term is None:
            raise TermNotFoundError(f"Term {term_id} not found")
        if term.status != "suggested":
            raise InvalidStatusTransitionError(
                f"Term must be in 'suggested' status to promote, got '{term.status}'"
            )
        snapshot = TermHistory(
            term_id=term.id,
            definition=term.definition,
            full_name=term.full_name,
            category=term.category,
            owner_id=term.owner_id,
            status=term.status,
            changed_by=by_user,
            change_note="Promoted from suggested to pending",
        )
        self._session.add(snapshot)
        term.status = "pending"
        term.version += 1
        await self._session.commit()
        await self._session.refresh(term)
        return term

    async def dismiss(self, term_id: UUID, by_user: UUID) -> None:
        """Discard a suggested term."""
        term = await self._session.get(Term, term_id)
        if term is None:
            raise TermNotFoundError(f"Term {term_id} not found")
        await self._session.delete(term)
        await self._session.commit()

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    async def get_history(self, term_id: UUID) -> list[TermHistory]:
        term = await self._session.get(Term, term_id)
        if term is None:
            raise TermNotFoundError(f"Term {term_id} not found")
        stmt = select(TermHistory).where(TermHistory.term_id == term_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def revert(self, term_id: UUID, history_id: UUID, by_user: UUID) -> Term:
        term = await self._session.get(Term, term_id)
        if term is None:
            raise TermNotFoundError(f"Term {term_id} not found")
        snapshot = await self._session.get(TermHistory, history_id)
        if snapshot is None or snapshot.term_id != term_id:
            raise TermNotFoundError(f"History entry {history_id} not found")

        # Snapshot current state before reverting
        pre_revert = TermHistory(
            term_id=term.id,
            definition=term.definition,
            full_name=term.full_name,
            category=term.category,
            owner_id=term.owner_id,
            status=term.status,
            changed_by=by_user,
            change_note=f"Reverted to history {history_id}",
        )
        self._session.add(pre_revert)

        if snapshot.definition is not None:
            term.definition = snapshot.definition
        if snapshot.full_name is not None:
            term.full_name = snapshot.full_name
        if snapshot.category is not None:
            term.category = snapshot.category
        term.version += 1

        await self._session.commit()
        await self._session.refresh(term)
        return term

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    async def add_relationship(
        self, term_id: UUID, related_term_id: UUID, relationship_type: str, created_by: UUID
    ) -> TermRelationship:
        term = await self._session.get(Term, term_id)
        if term is None:
            raise TermNotFoundError(f"Term {term_id} not found")
        rel = TermRelationship(
            term_id=term_id,
            related_term_id=related_term_id,
            relationship_type=relationship_type,
            created_by=created_by,
        )
        self._session.add(rel)
        await self._session.commit()
        await self._session.refresh(rel)
        return rel

    async def delete_relationship(self, term_id: UUID, rel_id: UUID) -> None:
        rel = await self._session.get(TermRelationship, rel_id)
        if rel is None or rel.term_id != term_id:
            raise RelationshipNotFoundError(f"Relationship {rel_id} not found")
        await self._session.delete(rel)
        await self._session.commit()
