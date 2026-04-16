"""Tests for AuditService."""

from lingo.models import AuditEvent
from lingo.services.audit_service import AuditService


class TestAuditService:
    async def test_log_creates_event(self, session, admin_user):
        svc = AuditService(session)
        event = await svc.log(
            "term.created",
            actor_id=admin_user.id,
            target_type="term",
            payload={"name": "SRE"},
        )
        assert event.id is not None
        assert event.action == "term.created"
        assert event.actor_id == admin_user.id
        assert event.target_type == "term"
        assert event.payload == {"name": "SRE"}

    async def test_log_without_optional_fields(self, session):
        svc = AuditService(session)
        event = await svc.log("setup.completed")
        assert event.action == "setup.completed"
        assert event.actor_id is None
        assert event.target_id is None
        assert event.payload is None

    async def test_list_returns_all_events(self, session, admin_user, member_user):
        svc = AuditService(session)
        await svc.log("term.created", actor_id=admin_user.id)
        await svc.log("term.deleted", actor_id=member_user.id)
        events = await svc.list()
        assert len(events) == 2
        actions = {e.action for e in events}
        assert actions == {"term.created", "term.deleted"}

    async def test_list_pagination(self, session, admin_user):
        svc = AuditService(session)
        for i in range(5):
            await svc.log(f"action.{i}", actor_id=admin_user.id)
        page1 = await svc.list(limit=3, offset=0)
        page2 = await svc.list(limit=3, offset=3)
        assert len(page1) == 3
        assert len(page2) == 2

    async def test_log_persisted_to_db(self, session, admin_user):
        svc = AuditService(session)
        event = await svc.log("token.created", actor_id=admin_user.id, target_type="token")
        row = await session.get(AuditEvent, event.id)
        assert row is not None
        assert row.action == "token.created"
