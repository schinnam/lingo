"""Tests for Phase 2 auth: OIDC JWT bearer + MCP API token bearer."""
import hashlib
import base64
import os
import uuid
from unittest.mock import patch, AsyncMock

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from lingo.models.base import Base
from lingo.models import User
from lingo.models.token import Token
from lingo.main import app
from lingo.db.session import get_session
from lingo.config import settings


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

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
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
        from datetime import datetime, timezone
        raw, token_hash = _make_api_token()
        async with test_session_factory() as sess:
            token = Token(
                user_id=client._admin.id,
                name="revoked-token",
                token_hash=token_hash,
                scopes=["read"],
                revoked_at=datetime.now(timezone.utc),
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
# OIDC JWT Bearer Auth
# ---------------------------------------------------------------------------

class TestOIDCJWTAuth:
    """get_current_user must validate a signed JWT and upsert/resolve a User by email."""

    async def test_valid_jwt_creates_user_if_not_exists(self, client, test_session_factory):
        """A valid JWT for an unknown email auto-provisions a member User."""
        from lingo.auth.oidc import make_test_jwt

        token = make_test_jwt(email="newuser@corp.example", name="New User")
        # POST /api/v1/terms requires CurrentUser (member+)
        resp = await client.post(
            "/api/v1/terms",
            json={"name": "NEWU", "definition": "new user term"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201

        # User should now exist in DB
        from sqlalchemy import select
        from lingo.models import User
        async with test_session_factory() as sess:
            result = await sess.execute(
                select(User).where(User.email == "newuser@corp.example")
            )
            user = result.scalar_one_or_none()
            assert user is not None
            assert user.role == "member"

    async def test_valid_jwt_resolves_existing_user(self, client):
        """A valid JWT for a known email resolves to the existing user."""
        from lingo.auth.oidc import make_test_jwt

        # admin@corp.example is seeded in db_users fixture
        token = make_test_jwt(email="admin@corp.example", name="Admin")
        resp = await client.get(
            _AUTH_ENDPOINT,  # admin-only endpoint
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200  # admin role preserved

    async def test_expired_jwt_returns_401(self, client):
        """An expired JWT must return 401."""
        from lingo.auth.oidc import make_test_jwt
        import time

        token = make_test_jwt(
            email="expired@corp.example",
            name="Expired",
            exp=int(time.time()) - 3600,  # 1 hour ago
        )
        resp = await client.get(
            _AUTHED_READ,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401

    async def test_invalid_signature_jwt_returns_401(self, client):
        """A JWT signed with a different key must return 401."""
        import jwt as pyjwt
        import time

        # Sign with a DIFFERENT secret than Lingo's
        payload = {
            "email": "hacker@evil.example",
            "name": "Hacker",
            "sub": "hacker-sub",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        }
        evil_token = pyjwt.encode(payload, "wrong-secret", algorithm="HS256")
        resp = await client.get(
            _AUTHED_READ,
            headers={"Authorization": f"Bearer {evil_token}"},
        )
        assert resp.status_code == 401

    async def test_jwt_missing_email_claim_returns_401(self, client):
        """A JWT without an email claim must return 401."""
        import jwt as pyjwt
        import time
        from lingo.config import settings

        payload = {
            "sub": "some-sub",
            "name": "No Email",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        }
        token = pyjwt.encode(payload, settings.secret_key, algorithm="HS256")
        resp = await client.get(
            _AUTHED_READ,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401
