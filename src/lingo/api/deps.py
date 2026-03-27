"""FastAPI dependencies: auth, session injection."""
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lingo.config import settings
from lingo.db.session import get_session
from lingo.models import User
from lingo.models.token import Token


def _parse_bearer(authorization: str | None) -> str | None:
    """Extract raw token from 'Authorization: Bearer <token>' header."""
    if authorization is None:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


async def _resolve_api_token(raw_token: str, session: AsyncSession) -> User | None:
    """Look up an API token by sha256 hash. Returns the owner User or None."""
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    result = await session.execute(
        select(Token).where(
            Token.token_hash == token_hash,
            Token.revoked_at.is_(None),
        )
    )
    token = result.scalar_one_or_none()
    if token is None:
        return None

    user = await session.get(User, token.user_id)
    if user is None or not user.is_active:
        return None

    # Update last_used_at
    token.last_used_at = datetime.now(timezone.utc)
    await session.commit()

    return user


async def _resolve_jwt(raw_token: str, session: AsyncSession) -> User | None:
    """Validate a JWT and upsert/resolve a User by email claim."""
    from lingo.auth.oidc import verify_jwt

    payload = verify_jwt(raw_token)
    if payload is None:
        return None

    email = payload.get("email")
    if not email:
        return None

    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        # Auto-provision new user as member
        display_name = payload.get("name") or email.split("@")[0]
        user = User(email=email, display_name=display_name, role="member")
        session.add(user)
        await session.commit()
        await session.refresh(user)

    if not user.is_active:
        return None

    return user


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    x_user_id: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_session),
) -> User:
    """Resolve the current user from one of three auth methods (in priority order):

    1. Authorization: Bearer <api_token>  — sha256 DB lookup (MCP tokens)
    2. Authorization: Bearer <jwt>        — OIDC JWT validation (SSO)
    3. X-User-Id: <uuid>                  — dev-mode bypass

    Bearer always takes priority over X-User-Id when both are present.
    """
    raw_token = _parse_bearer(authorization)

    if raw_token is not None:
        # Try API token first (faster — pure hash lookup, no crypto)
        user = await _resolve_api_token(raw_token, session)
        if user is not None:
            return user

        # Fall back to JWT validation
        user = await _resolve_jwt(raw_token, session)
        if user is not None:
            return user

        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Dev-mode: X-User-Id header (only allowed when dev_mode is enabled)
    if not settings.dev_mode or x_user_id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user_uuid = uuid.UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user id")

    user = await session.get(User, user_uuid)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_role(*roles: str):
    """Return a dependency that enforces the user has one of the given roles."""
    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return _check


CurrentUser = Annotated[User, Depends(get_current_user)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]
EditorUser = Annotated[User, Depends(require_role("editor", "admin"))]
AdminUser = Annotated[User, Depends(require_role("admin"))]
