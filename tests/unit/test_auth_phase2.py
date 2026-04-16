"""Tests for Phase 2 auth: OIDC JWT bearer + MCP API token bearer."""

import base64
import hashlib
import os
from datetime import UTC
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from lingo.config import settings
from lingo.db.session import get_session
from lingo.main import app
from lingo.models import User
from lingo.models.base import Base
from lingo.models.token import Token

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
    """Seed admin and member users; return their IDs and the session factory."""
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
    async def _override_get_session():
        async with test_session_factory() as sess:
            yield sess

    app.dependency_overrides[get_session] = _override_get_session
    settings.dev_mode = True

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac._admin = db_users["admin"]
        ac._member = db_users["member"]
        ac._admin_id = str(db_users["admin"].id)
        ac._member_id = str(db_users["member"].id)
        yield ac

    app.dependency_overrides.clear()
    settings.dev_mode = False


def _make_api_token(raw: str | None = None) -> tuple[str, str]:
    """Return (raw_token, token_hash) for seeding the DB."""
    if raw is None:
        raw = base64.urlsafe_b64encode(os.urandom(32)).decode("ascii").rstrip("=")
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, token_hash


# ---------------------------------------------------------------------------
# MCP Bearer Token Auth
# ---------------------------------------------------------------------------

_AUTH_ENDPOINT = "/api/v1/users"  # admin-only endpoint; requires CurrentUser + admin role
_MEMBER_ENDPOINT = "/api/v1/terms"  # list — public; use POST to test member auth
_AUTHED_READ = "/api/v1/admin/stats"  # admin-only read


class TestMCPBearerTokenAuth:
    """get_current_user must resolve a user via sha256(Bearer token) DB lookup."""

    async def test_valid_api_token_authenticates_user(self, client, test_session_factory):
        """A valid non-revoked admin API token resolves to admin user."""
        raw, token_hash = _make_api_token()
        async with test_session_factory() as sess:
            token = Token(
                user_id=client._admin.id,
                name="test-token",
                token_hash=token_hash,
                scopes=["read"],
            )
            sess.add(token)
            await sess.commit()

        resp = await client.get(
            _AUTHED_READ,
            headers={"Authorization": f"Bearer {raw}"},
        )
        assert resp.status_code == 200

    async def test_revoked_token_returns_401(self, client, test_session_factory):
        """A revoked token (revoked_at set) must not authenticate."""
        from datetime import datetime

        raw, token_hash = _make_api_token()
        async with test_session_factory() as sess:
            token = Token(
                user_id=client._admin.id,
                name="revoked-token",
                token_hash=token_hash,
                scopes=["read"],
                revoked_at=datetime.now(UTC),
            )
            sess.add(token)
            await sess.commit()

        resp = await client.get(
            _AUTHED_READ,
            headers={"Authorization": f"Bearer {raw}"},
        )
        assert resp.status_code == 401

    async def test_unknown_token_returns_401(self, client):
        """A token not in the DB must return 401."""
        raw = base64.urlsafe_b64encode(os.urandom(32)).decode("ascii").rstrip("=")
        resp = await client.get(
            _AUTHED_READ,
            headers={"Authorization": f"Bearer {raw}"},
        )
        assert resp.status_code == 401

    async def test_token_with_inactive_user_returns_401(self, client, test_session_factory):
        """A token belonging to an inactive user must not authenticate."""
        raw, token_hash = _make_api_token()
        async with test_session_factory() as sess:
            inactive = User(
                email="inactive@corp.example",
                display_name="Inactive",
                role="member",
                is_active=False,
            )
            sess.add(inactive)
            await sess.commit()
            await sess.refresh(inactive)
            token = Token(
                user_id=inactive.id,
                name="inactive-user-token",
                token_hash=token_hash,
                scopes=["read"],
            )
            sess.add(token)
            await sess.commit()

        resp = await client.get(
            _AUTHED_READ,
            headers={"Authorization": f"Bearer {raw}"},
        )
        assert resp.status_code == 401

    async def test_api_token_updates_last_used_at(self, client, test_session_factory):
        """A successful token auth should update last_used_at on the token row."""
        raw, token_hash = _make_api_token()
        async with test_session_factory() as sess:
            token = Token(
                user_id=client._admin.id,
                name="usage-tracked-token",
                token_hash=token_hash,
                scopes=["read"],
            )
            sess.add(token)
            await sess.commit()
            await sess.refresh(token)
            token_id = token.id

        await client.get(
            _AUTHED_READ,
            headers={"Authorization": f"Bearer {raw}"},
        )

        async with test_session_factory() as sess:
            refreshed = await sess.get(Token, token_id)
            assert refreshed.last_used_at is not None

    async def test_bearer_prefix_required(self, client, test_session_factory):
        """Authorization header without 'Bearer ' prefix must return 401."""
        raw, token_hash = _make_api_token()
        async with test_session_factory() as sess:
            token = Token(
                user_id=client._admin.id,
                name="bad-prefix-token",
                token_hash=token_hash,
                scopes=["read"],
            )
            sess.add(token)
            await sess.commit()

        resp = await client.get(
            _AUTHED_READ,
            headers={"Authorization": raw},  # no "Bearer " prefix
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Auth method priority: X-User-Id vs Bearer token
# ---------------------------------------------------------------------------


class TestAuthMethodPriority:
    """Both auth methods should work; Bearer token takes priority over X-User-Id."""

    async def test_no_auth_returns_401_on_protected_endpoint(self, client):
        resp = await client.get(_AUTHED_READ)
        assert resp.status_code == 401

    async def test_x_user_id_still_works(self, client):
        """X-User-Id header (dev mode) should still authenticate."""
        resp = await client.get(
            _AUTHED_READ,
            headers={"X-User-Id": client._admin_id},
        )
        assert resp.status_code == 200

    async def test_x_user_id_rejected_when_dev_mode_off(self, client):
        """X-User-Id must be rejected in production (dev_mode=False)."""
        settings.dev_mode = False
        try:
            resp = await client.get(
                _AUTHED_READ,
                headers={"X-User-Id": client._admin_id},
            )
            assert resp.status_code == 401
        finally:
            settings.dev_mode = True  # restore for remaining tests in fixture

    async def test_both_auth_headers_bearer_wins(self, client, test_session_factory):
        """When both X-User-Id and Authorization: Bearer are provided, Bearer token wins."""
        raw, token_hash = _make_api_token()
        async with test_session_factory() as sess:
            token = Token(
                user_id=client._member.id,  # member token
                name="dual-auth-token",
                token_hash=token_hash,
                scopes=["read"],
            )
            sess.add(token)
            await sess.commit()

        # admin X-User-Id + member Bearer token — member has no admin access
        resp = await client.get(
            _AUTH_ENDPOINT,  # admin-only endpoint
            headers={
                "X-User-Id": client._admin_id,
                "Authorization": f"Bearer {raw}",
            },
        )
        # Bearer token (member) should win → 403, not 200
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Slack OIDC Auth (replaces JWT-based TestOIDCJWTAuth)
# ---------------------------------------------------------------------------


class TestSlackOIDCAuth:
    """Slack OIDC callback creates/links users and establishes a session."""

    async def test_new_user_created_on_first_slack_signin(self, client, test_session_factory):
        """GET /auth/slack/callback creates a new User row on first Sign in with Slack."""
        from sqlalchemy import select

        from lingo.auth.slack_oidc import hmac_sign

        nonce = "test-nonce-newuser"
        state = hmac_sign(nonce, settings.secret_key)

        with (
            patch("lingo.api.routes.auth.exchange_code", new_callable=AsyncMock) as mock_exc,
            patch("lingo.api.routes.auth.get_user_info", new_callable=AsyncMock) as mock_info,
        ):
            mock_exc.return_value = {"access_token": "slack-token"}
            mock_info.return_value = {
                "sub": "U123",
                "email": "new@corp.com",
                "name": "New User",
            }

            resp = await client.get(
                f"/auth/slack/callback?code=abc&state={state}",
                cookies={"lingo_oauth_state": nonce},
            )

        assert resp.status_code in (302, 307)
        assert "session" in resp.cookies

        async with test_session_factory() as sess:
            result = await sess.execute(select(User).where(User.email == "new@corp.com"))
            user = result.scalar_one_or_none()
        assert user is not None
        assert user.slack_user_id == "U123"
        assert user.email == "new@corp.com"

    async def test_existing_user_gets_slack_user_id_linked(self, client, test_session_factory):
        """Existing user matched by email gets slack_user_id set; no duplicate row created."""
        from sqlalchemy import select

        from lingo.auth.slack_oidc import hmac_sign

        async with test_session_factory() as sess:
            existing = User(email="existing@corp.com", display_name="Existing", role="member")
            sess.add(existing)
            await sess.commit()

        nonce = "test-nonce-existing"
        state = hmac_sign(nonce, settings.secret_key)

        with (
            patch("lingo.api.routes.auth.exchange_code", new_callable=AsyncMock) as mock_exc,
            patch("lingo.api.routes.auth.get_user_info", new_callable=AsyncMock) as mock_info,
        ):
            mock_exc.return_value = {"access_token": "slack-token"}
            mock_info.return_value = {
                "sub": "U456",
                "email": "existing@corp.com",
                "name": "Existing",
            }

            resp = await client.get(
                f"/auth/slack/callback?code=abc&state={state}",
                cookies={"lingo_oauth_state": nonce},
            )

        assert resp.status_code in (302, 307)

        async with test_session_factory() as sess:
            result = await sess.execute(select(User).where(User.email == "existing@corp.com"))
            users = result.scalars().all()
        assert len(users) == 1  # no duplicate row
        assert users[0].slack_user_id == "U456"

    async def test_invalid_state_returns_400(self, client):
        """Tampered state param triggers CSRF check → 400, no session cookie set."""
        resp = await client.get(
            "/auth/slack/callback?code=abc&state=tampered-value",
            cookies={"lingo_oauth_state": "test-nonce-csrf"},
        )
        assert resp.status_code == 400
        assert "session" not in resp.cookies

    async def test_auth_me_without_and_with_session(self, client):
        """/auth/me → 401 without session; 200 with session returning user JSON."""
        # No session → 401
        resp = await client.get("/auth/me")
        assert resp.status_code == 401

        # Establish session via dev login (dev_mode=True in client fixture)
        login_resp = await client.get(f"/auth/dev/login?email={client._member.email}")
        assert login_resp.status_code in (302, 307)

        # Explicitly pass session cookie → 200
        me_resp = await client.get("/auth/me", cookies=login_resp.cookies)
        assert me_resp.status_code == 200
        data = me_resp.json()
        assert data["email"] == client._member.email


# ---------------------------------------------------------------------------
# API Token Ownership
# ---------------------------------------------------------------------------


class TestAPITokenOwnership:
    """Non-admin users can create/delete their own tokens; cannot delete others'."""

    async def test_member_token_crud_and_cross_user_forbidden(self, client, test_session_factory):
        """Member: POST /tokens → 201; DELETE own → 204; DELETE admin's token → 403."""
        # Establish member session via dev login
        login_resp = await client.get(f"/auth/dev/login?email={client._member.email}")
        assert login_resp.status_code in (302, 307)
        member_cookies = dict(login_resp.cookies)

        # Create token as member → 201, user_id matches member
        create_resp = await client.post(
            "/api/v1/tokens",
            json={"name": "member-token", "scopes": ["read"]},
            cookies=member_cookies,
        )
        assert create_resp.status_code == 201
        token_data = create_resp.json()
        assert token_data["user_id"] == client._member_id
        member_token_id = token_data["id"]

        # Seed an admin token directly in the DB (no auth flow needed)
        _, admin_token_hash = _make_api_token()
        async with test_session_factory() as sess:
            admin_tok = Token(
                user_id=client._admin.id,
                name="admin-token",
                token_hash=admin_token_hash,
                scopes=["read"],
            )
            sess.add(admin_tok)
            await sess.commit()
            await sess.refresh(admin_tok)
            admin_token_id = str(admin_tok.id)

        # Member cannot delete admin's token → 403
        del_other_resp = await client.delete(
            f"/api/v1/tokens/{admin_token_id}",
            cookies=member_cookies,
        )
        assert del_other_resp.status_code == 403

        # Member can delete own token → 204
        del_own_resp = await client.delete(
            f"/api/v1/tokens/{member_token_id}",
            cookies=member_cookies,
        )
        assert del_own_resp.status_code == 204
