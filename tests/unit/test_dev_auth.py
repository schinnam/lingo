"""Tests for custom X-Lingo-Dev-Auth header behavior."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from lingo.config import settings
from lingo.db.session import get_session
from lingo.main import app
from lingo.models import User
from lingo.models.base import Base


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
async def client(test_session_factory):
    async def _override_get_session():
        async with test_session_factory() as sess:
            yield sess

    app.dependency_overrides[get_session] = _override_get_session
    original_dev_mode = settings.dev_mode
    settings.dev_mode = True

    async with test_session_factory() as sess:
        user = User(email="dev@lingo.dev", display_name="Dev User", role="member")
        sess.add(user)
        await sess.commit()
        await sess.refresh(user)
        user_id = str(user.id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac._user_id = user_id
        yield ac

    app.dependency_overrides.clear()
    settings.dev_mode = original_dev_mode


class TestDevAuthHeader:
    async def test_dev_login_redirects_by_default(self, client):
        """By default, GET /auth/dev/login redirects to /."""
        resp = await client.get("/auth/dev/login?email=dev@lingo.dev")
        assert resp.status_code in (302, 307)
        assert resp.headers["location"] == "/"

    async def test_dev_login_returns_json_with_header(self, client):
        """With X-Lingo-Dev-Auth: true, GET /auth/dev/login returns JSON."""
        resp = await client.get(
            "/auth/dev/login?email=dev@lingo.dev", headers={"X-Lingo-Dev-Auth": "true"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "dev@lingo.dev"
        assert data["id"] == client._user_id

    async def test_dev_login_fails_in_production(self, client):
        """Dev login must return 404 when LINGO_DEV_MODE=false."""
        prev = settings.dev_mode
        settings.dev_mode = False
        try:
            resp = await client.get("/auth/dev/login?email=dev@lingo.dev")
            assert resp.status_code == 404
        finally:
            settings.dev_mode = prev
