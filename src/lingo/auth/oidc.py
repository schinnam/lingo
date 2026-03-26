"""OIDC / JWT auth helpers.

In production, tokens come from an OIDC provider (Google Workspace, Okta, generic OIDC).
In tests, use `make_test_jwt` to create a HS256-signed JWT with the app secret key.

Production flow:
  - OIDC provider issues a JWT (RS256 or HS256 depending on provider)
  - Client sends `Authorization: Bearer <jwt>` on every request
  - `verify_jwt` validates the token and extracts the email claim
  - `get_current_user` in deps.py upserts a User by email (auto-provisions on first login)

For simplicity in v1, we validate JWTs signed with `settings.secret_key` (HS256).
Real OIDC integration (RS256 + JWKS URL) can be wired in later via Authlib.
"""
import time
from typing import Optional

import jwt as pyjwt
from jwt.exceptions import ExpiredSignatureError, InvalidSignatureError, DecodeError

from lingo.config import settings


def verify_jwt(token: str) -> Optional[dict]:
    """Decode and validate a JWT signed with LINGO_SECRET_KEY (HS256).

    Returns the payload dict if valid, or None if invalid/expired.
    The caller must check for the `email` claim.
    """
    try:
        payload = pyjwt.decode(
            token,
            settings.secret_key,
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
    return pyjwt.encode(payload, settings.secret_key, algorithm="HS256")
