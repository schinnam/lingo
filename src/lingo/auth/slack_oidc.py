"""Slack OpenID Connect auth helpers + JWT utilities.

Slack OIDC flow:
  1. build_auth_url(state) → redirect user to Slack
  2. exchange_code(code) → get access_token from Slack
  3. get_user_info(access_token) → get sub/email/name from Slack
  4. upsert_user(...) → create or update local User row

JWT helpers (moved from oidc.py) are also kept here for the existing
Bearer-JWT auth path in deps.py and for test token creation.
"""
import hashlib
import hmac as _hmac
import time
import urllib.parse
from typing import Optional

import httpx
import jwt as pyjwt
from jwt.exceptions import DecodeError, ExpiredSignatureError, InvalidSignatureError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from lingo.config import settings
from lingo.models import User


# ---------------------------------------------------------------------------
# AuthError
# ---------------------------------------------------------------------------

class AuthError(Exception):
    """Raised when a Slack auth step fails. Never include secrets in `code`."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


# ---------------------------------------------------------------------------
# HMAC helpers
# ---------------------------------------------------------------------------

def hmac_sign(value: str, secret: str) -> str:
    """Return a hex HMAC-SHA256 signature of value using secret."""
    return _hmac.new(secret.encode(), value.encode(), "sha256").hexdigest()


# ---------------------------------------------------------------------------
# Slack OIDC helpers
# ---------------------------------------------------------------------------

_SLACK_AUTHORIZE_URL = "https://slack.com/openid/connect/authorize"
_SLACK_TOKEN_URL = "https://slack.com/api/openid.connect.token"
_SLACK_USERINFO_URL = "https://slack.com/api/openid.connect.userInfo"


def build_auth_url(state: str) -> str:
    """Return the Slack OpenID Connect authorization URL."""
    params = {
        "client_id": settings.slack_client_id,
        "scope": "openid email profile",
        "redirect_uri": settings.app_url + "/auth/slack/callback",
        "response_type": "code",
        "state": state,
    }
    return f"{_SLACK_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


async def exchange_code(code: str) -> dict:
    """Exchange an authorization code for an access token from Slack.

    Raises AuthError("token_exchange_failed") on any HTTP or API error.
    client_secret is never included in exception messages or logs.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                _SLACK_TOKEN_URL,
                data={
                    "client_id": settings.slack_client_id,
                    "client_secret": settings.slack_client_secret,
                    "code": code,
                    "redirect_uri": settings.app_url + "/auth/slack/callback",
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
            body = response.json()
            if not body.get("ok"):
                raise AuthError("token_exchange_failed")
            return body
    except AuthError:
        raise
    except Exception:
        raise AuthError("token_exchange_failed")


async def get_user_info(access_token: str) -> dict:
    """Fetch user info from Slack using the given access token.

    Returns a dict with at least: sub, email, name.
    Raises AuthError("userinfo_failed") on any error.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                _SLACK_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            body = response.json()
            if not body.get("ok"):
                raise AuthError("userinfo_failed")
            return body
    except AuthError:
        raise
    except Exception:
        raise AuthError("userinfo_failed")


async def upsert_user(
    slack_user_id: str,
    email: str,
    display_name: str,
    session: AsyncSession,
) -> User:
    """Upsert a User row based on Slack user info.

    Lookup order:
    1. By slack_user_id → update email/display_name if changed
    2. By email → set slack_user_id, update display_name
    3. Neither → create new User with role="member"
    4. IntegrityError on create (race) → re-query and return existing user
    """
    # 1. Lookup by slack_user_id
    result = await session.execute(
        select(User).where(User.slack_user_id == slack_user_id)
    )
    user = result.scalar_one_or_none()
    if user is not None:
        if user.email != email:
            user.email = email
        if user.display_name != display_name:
            user.display_name = display_name
        await session.commit()
        return user

    # 2. Lookup by email
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is not None:
        user.slack_user_id = slack_user_id
        if user.display_name != display_name:
            user.display_name = display_name
        await session.commit()
        return user

    # 3. Create new user
    try:
        user = User(
            email=email,
            display_name=display_name,
            slack_user_id=slack_user_id,
            role="member",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
    except IntegrityError:
        await session.rollback()
        # 4. Race on unique constraint — re-query and return existing row
        result = await session.execute(
            select(User).where(User.slack_user_id == slack_user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            result = await session.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
        return user


# ---------------------------------------------------------------------------
# JWT helpers (moved from oidc.py — used by deps.py and tests)
# ---------------------------------------------------------------------------

def _derive_signing_key(secret: str) -> bytes:
    """Derive a 32-byte key from the secret to satisfy HMAC-SHA256 minimum length (RFC 7518 §3.2)."""
    return hashlib.sha256(secret.encode()).digest()


def verify_jwt(token: str) -> Optional[dict]:
    """Decode and validate a JWT signed with LINGO_SECRET_KEY (HS256).

    Returns the payload dict if valid, or None if invalid/expired.
    The caller must check for the `email` claim.
    """
    try:
        payload = pyjwt.decode(
            token,
            _derive_signing_key(settings.secret_key),
            algorithms=["HS256"],
            options={"require": ["exp", "email"]},
        )
        return payload
    except (ExpiredSignatureError, InvalidSignatureError, DecodeError, Exception):
        return None


def make_test_jwt(
    email: str,
    name: str = "Test User",
    exp: Optional[int] = None,
    sub: Optional[str] = None,
) -> str:
    """Create a HS256-signed JWT for testing. Uses `settings.secret_key`."""
    now = int(time.time())
    payload = {
        "sub": sub or f"test|{email}",
        "email": email,
        "name": name,
        "iat": now,
        "exp": exp if exp is not None else now + 3600,
    }
    return pyjwt.encode(payload, _derive_signing_key(settings.secret_key), algorithm="HS256")
