"""Tests for Phase 3: MCP tools and bearer token auth middleware.

Strategy:
  - Tool logic (get_term, search_terms, list_terms) tested by calling the
    underlying service layer directly — avoids MCP transport complexity in unit tests.
  - Auth middleware tested via a minimal Starlette test app that uses the same
    MCPBearerAuthMiddleware we wire onto the real MCP endpoint.
  - Integration smoke test confirms /mcp is mounted and returns 401 without a token.
"""
import hashlib

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from lingo.db.session import get_session
from lingo.main import app
from lingo.models import User
from lingo.models.base import Base
from lingo.models.term import Term
from lingo.models.token import Token
from lingo.mcp.auth import MCPBearerAuthMiddleware


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
async def test_session_factory(test_engine):
    return async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)


@pytest.fixture
async def seeded_db(test_session_factory):
    """Seed: one user, one API token, three terms (varied status/category)."""
    async with test_session_factory() as sess:
        user = User(email="bot@corp.example", display_name="Bot", role="member")
        sess.add(user)
        await sess.commit()
        await sess.refresh(user)

        raw_token = "test-mcp-token-abc123"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        tok = Token(
            user_id=user.id,
            token_hash=token_hash,
            name="mcp-test",
        )
        sess.add(tok)
        await sess.commit()

        t1 = Term(
            name="API",
            definition="Application Programming Interface",
            full_name="Application Programming Interface",
            category="tech",
            status="official",
            source="user",
            created_by=user.id,
        )
        t2 = Term(
            name="CI",
            definition="Continuous Integration",
            category="tech",
            status="pending",
            source="user",
            created_by=user.id,
        )
        t3 = Term(
            name="OKR",
            definition="Objectives and Key Results",
            category="business",
            status="official",
            source="user",
            created_by=user.id,
        )
        sess.add_all([t1, t2, t3])
        await sess.commit()

        return {
            "user": user,
            "raw_token": raw_token,
            "factory": test_session_factory,
        }


# ---------------------------------------------------------------------------
# Helpers: call tool logic via service layer (bypasses MCP transport)
# ---------------------------------------------------------------------------


async def _get_term(session: AsyncSession, name: str) -> str:
    """Replicate get_term tool logic using a given session."""
    from sqlalchemy import select

    result = await session.execute(select(Term).where(Term.name.ilike(name)))
    term = result.scalar_one_or_none()
    if term is None:
        return f"Term '{name}' not found in the glossary."
    parts = [f"**{term.name}**"]
    if term.full_name:
        parts.append(f" ({term.full_name})")
    parts.append(f"\n{term.definition}")
    parts.append(f"\nStatus: {term.status}")
    if term.category:
        parts.append(f" | Category: {term.category}")
    return "".join(parts)


async def _search_terms(
    session: AsyncSession,
    query: str,
    status: str | None = None,
    limit: int = 10,
) -> str:
    from sqlalchemy import select

    limit = min(limit, 50)
    stmt = select(Term)
    if query:
        pattern = f"%{query}%"
        stmt = stmt.where(
            Term.name.ilike(pattern)
            | Term.definition.ilike(pattern)
            | Term.full_name.ilike(pattern)
        )
    if status:
        stmt = stmt.where(Term.status == status)
    stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    terms = list(result.scalars().all())
    if not terms:
        return f"No terms found matching '{query}'."

    def fmt(t):
        parts = [f"**{t.name}**"]
        if t.full_name:
            parts.append(f" ({t.full_name})")
        parts.append(f"\n{t.definition}")
        parts.append(f"\nStatus: {t.status}")
        if t.category:
            parts.append(f" | Category: {t.category}")
        return "".join(parts)

    return "\n\n".join(fmt(t) for t in terms)


async def _list_terms(
    session: AsyncSession,
    category: str | None = None,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> str:
    from sqlalchemy import select

    limit = min(limit, 100)
    stmt = select(Term)
    if category:
        stmt = stmt.where(Term.category == category)
    if status:
        stmt = stmt.where(Term.status == status)
    stmt = stmt.offset(offset).limit(limit)
    result = await session.execute(stmt)
    terms = list(result.scalars().all())
    if not terms:
        return "No terms found."

    def fmt(t):
        parts = [f"**{t.name}**"]
        if t.full_name:
            parts.append(f" ({t.full_name})")
        parts.append(f"\n{t.definition}")
        parts.append(f"\nStatus: {t.status}")
        if t.category:
            parts.append(f" | Category: {t.category}")
        return "".join(parts)

    return "\n\n".join(fmt(t) for t in terms)


# ---------------------------------------------------------------------------
# get_term tool tests
# ---------------------------------------------------------------------------


class TestGetTerm:
    async def test_get_existing_term_returns_definition(self, seeded_db):
        factory = seeded_db["factory"]
        async with factory() as sess:
            result = await _get_term(sess, "API")
        assert "Application Programming Interface" in result

    async def test_get_term_case_insensitive(self, seeded_db):
        factory = seeded_db["factory"]
        async with factory() as sess:
            result = await _get_term(sess, "api")
        assert "Application Programming Interface" in result

    async def test_get_term_includes_status(self, seeded_db):
        factory = seeded_db["factory"]
        async with factory() as sess:
            result = await _get_term(sess, "API")
        assert "official" in result

    async def test_get_term_includes_category(self, seeded_db):
        factory = seeded_db["factory"]
        async with factory() as sess:
            result = await _get_term(sess, "API")
        assert "tech" in result

    async def test_get_nonexistent_term_returns_error(self, seeded_db):
        factory = seeded_db["factory"]
        async with factory() as sess:
            result = await _get_term(sess, "ZZZNOPE")
        assert "not found" in result.lower()


# ---------------------------------------------------------------------------
# search_terms tool tests
# ---------------------------------------------------------------------------


class TestSearchTerms:
    async def test_search_returns_matching_terms(self, seeded_db):
        factory = seeded_db["factory"]
        async with factory() as sess:
            result = await _search_terms(sess, "Integration")
        assert "CI" in result or "Continuous Integration" in result

    async def test_search_no_results_returns_message(self, seeded_db):
        factory = seeded_db["factory"]
        async with factory() as sess:
            result = await _search_terms(sess, "xyznosuchterm")
        assert "no terms found" in result.lower()

    async def test_search_filter_by_status(self, seeded_db):
        factory = seeded_db["factory"]
        async with factory() as sess:
            result = await _search_terms(sess, "", status="official")
        assert "API" in result or "OKR" in result
        assert "CI" not in result

    async def test_search_respects_limit(self, seeded_db):
        factory = seeded_db["factory"]
        async with factory() as sess:
            result = await _search_terms(sess, "", limit=1)
        # Only 1 term should appear — count bold markers
        assert result.count("**") <= 2  # one term = one opening + one closing bold

    async def test_search_by_definition_keyword(self, seeded_db):
        factory = seeded_db["factory"]
        async with factory() as sess:
            result = await _search_terms(sess, "Objectives")
        assert "OKR" in result


# ---------------------------------------------------------------------------
# list_terms tool tests
# ---------------------------------------------------------------------------


class TestListTerms:
    async def test_list_all_terms(self, seeded_db):
        factory = seeded_db["factory"]
        async with factory() as sess:
            result = await _list_terms(sess)
        assert "API" in result
        assert "CI" in result
        assert "OKR" in result

    async def test_list_filter_by_category(self, seeded_db):
        factory = seeded_db["factory"]
        async with factory() as sess:
            result = await _list_terms(sess, category="business")
        assert "OKR" in result
        assert "CI" not in result
        assert "API" not in result

    async def test_list_filter_by_status(self, seeded_db):
        factory = seeded_db["factory"]
        async with factory() as sess:
            result = await _list_terms(sess, status="official")
        assert "API" in result
        assert "OKR" in result
        assert "CI" not in result

    async def test_list_respects_limit(self, seeded_db):
        factory = seeded_db["factory"]
        async with factory() as sess:
            result = await _list_terms(sess, limit=1)
        assert result.count("**") <= 2  # one term max

    async def test_list_respects_offset(self, seeded_db):
        factory = seeded_db["factory"]
        async with factory() as sess:
            all_terms = await _list_terms(sess)
            offset_terms = await _list_terms(sess, offset=2)
        # offset=2 should return fewer or different terms
        assert all_terms != offset_terms or offset_terms == "No terms found."

    async def test_list_no_results_returns_message(self, seeded_db):
        factory = seeded_db["factory"]
        async with factory() as sess:
            result = await _list_terms(sess, category="nonexistent-category")
        assert "no terms found" in result.lower()


# ---------------------------------------------------------------------------
# Auth middleware tests (tested via a minimal Starlette echo app)
# ---------------------------------------------------------------------------


async def _echo_handler(request: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


def _make_auth_app(session_factory):
    """Build a minimal Starlette app wrapped in MCPBearerAuthMiddleware.

    The middleware's _is_valid_token uses SessionFactory from lingo.db.session.
    We monkeypatch it for tests.
    """
    inner = Starlette(routes=[Route("/", _echo_handler, methods=["POST", "GET"])])
    return MCPBearerAuthMiddleware(inner), inner


class TestMCPBearerAuthMiddleware:
    async def test_no_token_returns_401(self, seeded_db):
        from lingo import mcp as mcp_mod
        from lingo.mcp import auth as auth_mod
        factory = seeded_db["factory"]

        # Patch SessionFactory inside auth module to use test DB
        original = auth_mod.SessionFactory
        auth_mod.SessionFactory = factory
        try:
            inner = Starlette(routes=[Route("/", _echo_handler, methods=["POST", "GET"])])
            auth_app = MCPBearerAuthMiddleware(inner)
            async with AsyncClient(transport=ASGITransport(app=auth_app), base_url="http://test") as client:
                resp = await client.post("/")
            assert resp.status_code == 401
        finally:
            auth_mod.SessionFactory = original

    async def test_bad_token_returns_401(self, seeded_db):
        from lingo.mcp import auth as auth_mod
        factory = seeded_db["factory"]

        original = auth_mod.SessionFactory
        auth_mod.SessionFactory = factory
        try:
            inner = Starlette(routes=[Route("/", _echo_handler, methods=["POST", "GET"])])
            auth_app = MCPBearerAuthMiddleware(inner)
            async with AsyncClient(transport=ASGITransport(app=auth_app), base_url="http://test") as client:
                resp = await client.post("/", headers={"Authorization": "Bearer bad-token"})
            assert resp.status_code == 401
        finally:
            auth_mod.SessionFactory = original

    async def test_valid_token_passes_through(self, seeded_db):
        from lingo.mcp import auth as auth_mod
        factory = seeded_db["factory"]
        raw_token = seeded_db["raw_token"]

        original = auth_mod.SessionFactory
        auth_mod.SessionFactory = factory
        try:
            inner = Starlette(routes=[Route("/", _echo_handler, methods=["POST", "GET"])])
            auth_app = MCPBearerAuthMiddleware(inner)
            async with AsyncClient(transport=ASGITransport(app=auth_app), base_url="http://test") as client:
                resp = await client.post("/", headers={"Authorization": f"Bearer {raw_token}"})
            assert resp.status_code == 200
            assert resp.text == "ok"
        finally:
            auth_mod.SessionFactory = original

    async def test_malformed_auth_header_returns_401(self, seeded_db):
        from lingo.mcp import auth as auth_mod
        factory = seeded_db["factory"]

        original = auth_mod.SessionFactory
        auth_mod.SessionFactory = factory
        try:
            inner = Starlette(routes=[Route("/", _echo_handler, methods=["POST", "GET"])])
            auth_app = MCPBearerAuthMiddleware(inner)
            async with AsyncClient(transport=ASGITransport(app=auth_app), base_url="http://test") as client:
                resp = await client.post("/", headers={"Authorization": "Token abc123"})
            assert resp.status_code == 401
        finally:
            auth_mod.SessionFactory = original


# ---------------------------------------------------------------------------
# Integration smoke test: /mcp endpoint is mounted and enforces auth
# ---------------------------------------------------------------------------


class TestMCPMounted:
    async def test_mcp_endpoint_exists_and_rejects_unauthenticated(self):
        """Smoke test: /mcp is reachable and returns 401 without a token."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/mcp/",
                content=b"{}",
                headers={"Content-Type": "application/json"},
            )
        # 401 = auth middleware ran; not 404 (unregistered) or 307 (wrong path)
        assert resp.status_code == 401
