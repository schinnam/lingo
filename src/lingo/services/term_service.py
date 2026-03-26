"""Term CRUD service layer."""
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lingo.models.term import Term
from lingo.models.term_history import TermHistory


class TermNotFoundError(Exception):
    pass


class VersionConflictError(Exception):
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
        full_name: Optional[str] = None,
        category: Optional[str] = None,
        source: str = "user",
    ) -> Term:
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
        q: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
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
        definition: Optional[str] = None,
        full_name: Optional[str] = None,
        category: Optional[str] = None,
        change_note: Optional[str] = None,
    ) -> Term:
        term = await self._session.get(Term, term_id)
        if term is None:
            raise TermNotFoundError(f"Term {term_id} not found")
        if term.version != version:
            raise VersionConflictError(
                f"Version conflict: expected {term.version}, got {version}"
            )

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
