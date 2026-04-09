"""Tests for Phase 2B auth: session cookie routes (/auth/slack/*, /auth/dev/login, /auth/me, /auth/logout)."""
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from lingo.auth.slack_oidc import hmac_sign
from lingo.config import settings
from lingo.db.session import get_session
from lingo.main import app
from lingo.models import User
from lingo.models.base import Base


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
async def db_users(test_session_factory):
    async with test_session_factory() as sess:
        admin = User(email="admin@corp.example", display_name="Admin", role="admin")
        member = User(email="member@corp.example", display_name="Member", role="member")
        sess.add_all([admin, member])
        await sess.commit()
        for u in [admin, member]:
            await sess.refresh(u)
        return {"admin": admin, "member": member}


@pytest.fixture
async def client(test_session_factory, db_users):
    async def _override():
        async with test_session_factory() as sess:
            yield sess

    app.dependency_overrides[get_session] = _override
    prev_dev = settings.dev_mode
    prev_secret = settings.secret_key
    settings.dev_mode = True
    settings.secret_key = "test-secret-key"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=False,
    ) as c:
        yield c, db_users

    app.dependency_overrides.pop(get_session, None)
    settings.dev_mode = prev_dev
    settings.secret_key = prev_secret


# ---------------------------------------------------------------------------
# Helper: extract session cookie value from a response
# ---------------------------------------------------------------------------

def _get_session_cookies(response):
    """Return set-cookie headers as dict."""
    return {c.name: c for c in response.cookies.jar}


# ---------------------------------------------------------------------------
# GET /auth/slack/login
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_slack_login_redirects(client):
    c, _ = client
    resp = await c.get("/auth/slack/login")
    assert resp.status_code in (302, 307)
    assert "slack.com" in resp.headers["location"]


@pytest.mark.asyncio
async def test_slack_login_sets_state_cookie(client):
    c, _ = client
    resp = await c.get("/auth/slack/login")
    assert "lingo_oauth_state" in resp.cookies


# ---------------------------------------------------------------------------
# GET /auth/slack/callback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_slack_callback_valid(client, db_users):
    c, users = client
    # First get a real nonce via /login
    login_resp = await c.get("/auth/slack/login")
    nonce = login_resp.cookies["lingo_oauth_state"]
    state = hmac_sign(nonce, settings.secret_key)

    admin = users["admin"]
    mock_user_info = {"ok": True, "sub": "U123", "email": admin.email, "name": admin.display_name}

    with (
        patch("lingo.api.routes.auth.exchange_code", new_callable=AsyncMock) as mock_exchange,
        patch("lingo.api.routes.auth.get_user_info", new_callable=AsyncMock) as mock_userinfo,
        patch("lingo.api.routes.auth.upsert_user", new_callable=AsyncMock) as mock_upsert,
    ):
        mock_exchange.return_value = {"ok": True, "access_token": "xoxp-test"}
        mock_userinfo.return_value = mock_user_info
        mock_upsert.return_value = admin

        resp = await c.get(
            f"/auth/slack/callback?code=testcode&state={state}",
            cookies={"lingo_oauth_state": nonce},
        )

    assert resp.status_code in (302, 307)
    assert resp.headers["location"] == "/"


@pytest.mark.asyncio
async def test_slack_callback_bad_state(client):
    c, _ = client
    nonce = "some-nonce"
    bad_state = "wrong-signature"
    resp = await c.get(
        f"/auth/slack/callback?code=abc&state={bad_state}",
        cookies={"lingo_oauth_state": nonce},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_slack_callback_missing_cookie(client):
    c, _ = client
    resp = await c.get("/auth/slack/callback?code=abc&state=anything")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_auth_me_no_session(client):
    c, _ = client
    resp = await c.get("/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_with_valid_session(client, db_users):
    c, users = client
    admin = users["admin"]

    # Use dev login to establish a session
    resp = await c.get(f"/auth/dev/login?email={admin.email}")
    assert resp.status_code in (302, 307)

    # Follow redirect manually (follow_redirects=False so we keep cookies)
    me_resp = await c.get("/auth/me", cookies=resp.cookies)
    assert me_resp.status_code == 200
    data = me_resp.json()
    assert data["email"] == admin.email
    assert data["role"] == admin.role


@pytest.mark.asyncio
async def test_auth_me_inactive_user(client, test_session_factory, db_users):
    c, users = client
    admin = users["admin"]

    # Deactivate user
    async with test_session_factory() as sess:
        u = await sess.get(User, admin.id)
        u.is_active = False
        await sess.commit()

    # Get session for inactive user directly via dev login
    login_resp = await c.get(f"/auth/dev/login?email={admin.email}")
    me_resp = await c.get("/auth/me", cookies=login_resp.cookies)
    assert me_resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_logout_clears_session(client, db_users):
    c, users = client
    admin = users["admin"]

    login_resp = await c.get(f"/auth/dev/login?email={admin.email}")
    session_cookies = dict(login_resp.cookies)

    logout_resp = await c.post("/auth/logout", cookies=session_cookies)
    assert logout_resp.status_code == 200
    assert logout_resp.json() == {"ok": True}

    # After logout, /auth/me should return 401
    me_resp = await c.get("/auth/me", cookies=logout_resp.cookies)
    assert me_resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /auth/dev/login
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dev_login_existing_user(client, db_users):
    c, users = client
    admin = users["admin"]
    resp = await c.get(f"/auth/dev/login?email={admin.email}")
    assert resp.status_code in (302, 307)
    assert resp.headers["location"] == "/"


@pytest.mark.asyncio
async def test_dev_login_creates_new_user(client, test_session_factory):
    c, _ = client
    new_email = "brandnew@corp.example"
    resp = await c.get(f"/auth/dev/login?email={new_email}")
    assert resp.status_code in (302, 307)

    # Verify user was created
    async with test_session_factory() as sess:
        from sqlalchemy import select
        result = await sess.execute(select(User).where(User.email == new_email))
        user = result.scalar_one_or_none()
    assert user is not None
    assert user.role == "member"


@pytest.mark.asyncio
async def test_dev_login_disabled_in_production(client):
    c, _ = client
    prev = settings.dev_mode
    settings.dev_mode = False
    try:
        resp = await c.get("/auth/dev/login?email=admin@corp.example")
        assert resp.status_code == 404
    finally:
        settings.dev_mode = prev


# ---------------------------------------------------------------------------
# Session cookie as priority-2 auth in get_current_user (deps.py)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_session_cookie_auth_via_api_endpoint(client, db_users):
    """Session cookie should authenticate requests to regular API endpoints."""
    c, users = client
    admin = users["admin"]

    # Establish session via dev login
    login_resp = await c.get(f"/auth/dev/login?email={admin.email}")
    session_cookies = dict(login_resp.cookies)

    # Access a protected endpoint using only the session cookie (no Bearer header)
    resp = await c.get("/api/v1/tokens", cookies=session_cookies)
    assert resp.status_code == 200
