from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lingo.models.audit_event import AuditEvent


class AuditService:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def log(
        self,
        action: str,
        *,
        actor_id: Optional[UUID] = None,
        target_type: Optional[str] = None,
        target_id: Optional[UUID] = None,
        payload: Optional[dict] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            payload=payload,
        )
        self._session.add(event)
        await self._session.commit()
        return event

    async def list(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEvent]:
        stmt = (
            select(AuditEvent)
            .order_by(AuditEvent.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
