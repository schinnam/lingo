"""FastAPI dependencies: auth, session injection."""
import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from lingo.db.session import get_session
from lingo.models import User


async def get_current_user(
    x_user_id: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_session),
) -> User:
    """Dev-mode auth: resolve user from X-User-Id header.

    In production this is replaced by OIDC session middleware.
    """
    if x_user_id is None:
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
