"""Tests for the TermService CRUD layer."""

import pytest
from sqlalchemy import select

from lingo.models import Term, TermHistory
from lingo.services.term_service import (
    RESERVED_TERM_NAMES,
    ReservedNameError,
    TermNotFoundError,
    TermService,
    VersionConflictError,
)


class TestCreateTerm:
    async def test_create_returns_term(self, session, member_user):
        svc = TermService(session)
        term = await svc.create(
            name="BART",
            definition="Business Arts Resource Tool",
            created_by=member_user.id,
        )
        assert term.id is not None
        assert term.name == "BART"
        assert term.status == "pending"
        assert term.source == "user"
        assert term.version == 1

    async def test_create_with_optional_fields(self, session, member_user):
        svc = TermService(session)
        term = await svc.create(
            name="SRE",
            definition="Site Reliability Engineering",
            full_name="Site Reliability Engineering",
            category="Eng",
            created_by=member_user.id,
        )
        assert term.full_name == "Site Reliability Engineering"
        assert term.category == "Eng"

    async def test_created_term_persisted(self, session, member_user):
        svc = TermService(session)
        term = await svc.create(
            name="CI", definition="Continuous Integration", created_by=member_user.id
        )
        row = await session.get(Term, term.id)
        assert row is not None
        assert row.name == "CI"


class TestReservedNames:
    async def test_reserved_name_raises(self, session, member_user):
        svc = TermService(session)
        with pytest.raises(ReservedNameError):
            await svc.create(name="define", definition="some definition", created_by=member_user.id)

    async def test_reserved_name_case_insensitive(self, session, member_user):
        svc = TermService(session)
        for variant in ("DEFINE", "Define", "ADD", "Export"):
            with pytest.raises(ReservedNameError):
                await svc.create(
                    name=variant, definition="some definition", created_by=member_user.id
                )

    async def test_all_reserved_names_blocked(self, session, member_user):
        svc = TermService(session)
        for name in RESERVED_TERM_NAMES:
            with pytest.raises(ReservedNameError):
                await svc.create(name=name, definition="some definition", created_by=member_user.id)

    async def test_non_reserved_name_allowed(self, session, member_user):
        svc = TermService(session)
        term = await svc.create(
            name="BART", definition="Business Arts Resource Tool", created_by=member_user.id
        )
        assert term.name == "BART"


class TestGetTerm:
    async def test_get_existing_term(self, session, member_user):
        svc = TermService(session)
        created = await svc.create(
            name="CD", definition="Continuous Deployment", created_by=member_user.id
        )
        fetched = await svc.get(created.id)
        assert fetched.id == created.id
        assert fetched.name == "CD"

    async def test_get_missing_raises(self, session):
        import uuid

        svc = TermService(session)
        with pytest.raises(TermNotFoundError):
            await svc.get(uuid.uuid4())


class TestListTerms:
    async def test_list_all(self, session, member_user):
        svc = TermService(session)
        await svc.create(name="A", definition="Alpha", created_by=member_user.id)
        await svc.create(name="B", definition="Beta", created_by=member_user.id)
        terms = await svc.list()
        assert len(terms) >= 2

    async def test_list_filter_by_status(self, session, member_user):
        svc = TermService(session)
        t = await svc.create(name="X", definition="X term", created_by=member_user.id)
        # Manually set one to official
        t.status = "official"
        await session.commit()

        official = await svc.list(status="official")
        pending = await svc.list(status="pending")
        assert all(r.status == "official" for r in official)
        assert all(r.status == "pending" for r in pending)

    async def test_list_filter_by_category(self, session, member_user):
        svc = TermService(session)
        await svc.create(
            name="DNS", definition="Domain Name System", category="Eng", created_by=member_user.id
        )
        await svc.create(
            name="OKR",
            definition="Objectives and Key Results",
            category="Ops",
            created_by=member_user.id,
        )

        eng = await svc.list(category="Eng")
        assert all(r.category == "Eng" for r in eng)

    async def test_list_search(self, session, member_user):
        svc = TermService(session)
        await svc.create(
            name="API", definition="Application Programming Interface", created_by=member_user.id
        )
        await svc.create(name="PR", definition="Pull Request", created_by=member_user.id)

        results = await svc.list(q="Pull")
        assert any(r.name == "PR" for r in results)


class TestUpdateTerm:
    async def test_update_definition(self, session, member_user):
        svc = TermService(session)
        term = await svc.create(
            name="MVP", definition="Minimum Viable Product", created_by=member_user.id
        )
        updated = await svc.update(
            term_id=term.id,
            version=1,
            updated_by=member_user.id,
            definition="Most Valuable Player",
        )
        assert updated.definition == "Most Valuable Player"
        assert updated.version == 2

    async def test_update_creates_history(self, session, member_user):
        svc = TermService(session)
        term = await svc.create(
            name="ROI", definition="Return on Investment", created_by=member_user.id
        )
        await svc.update(
            term_id=term.id,
            version=1,
            updated_by=member_user.id,
            definition="Return on Insight",
            change_note="Updated for new usage",
        )
        history = (
            (await session.execute(select(TermHistory).where(TermHistory.term_id == term.id)))
            .scalars()
            .all()
        )
        assert len(history) == 1
        assert history[0].change_note == "Updated for new usage"

    async def test_update_wrong_version_raises(self, session, member_user):
        svc = TermService(session)
        term = await svc.create(
            name="KPI", definition="Key Performance Indicator", created_by=member_user.id
        )
        with pytest.raises(VersionConflictError):
            await svc.update(
                term_id=term.id,
                version=99,  # wrong version
                updated_by=member_user.id,
                definition="Key Progress Indicator",
            )

    async def test_update_missing_term_raises(self, session, member_user):
        import uuid

        svc = TermService(session)
        with pytest.raises(TermNotFoundError):
            await svc.update(
                term_id=uuid.uuid4(),
                version=1,
                updated_by=member_user.id,
                definition="...",
            )


class TestDeleteTerm:
    async def test_delete_removes_term(self, session, member_user):
        svc = TermService(session)
        term = await svc.create(
            name="TBD", definition="To Be Determined", created_by=member_user.id
        )
        await svc.delete(term.id)
        row = await session.get(Term, term.id)
        assert row is None

    async def test_delete_missing_raises(self, session):
        import uuid

        svc = TermService(session)
        with pytest.raises(TermNotFoundError):
            await svc.delete(uuid.uuid4())
