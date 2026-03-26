"""REST routes for /api/v1/users."""
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from lingo.api.deps import AdminUser, SessionDep
from lingo.api.schemas import RolePatch, UserResponse
from lingo.models.user import User

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
async def list_users(session: SessionDep, admin: AdminUser):
    result = await session.execute(select(User))
    return list(result.scalars().all())


@router.patch("/{user_id}/role", response_model=UserResponse)
async def patch_user_role(user_id: UUID, body: RolePatch, session: SessionDep, admin: AdminUser):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = body.role
    await session.commit()
    await session.refresh(user)
    return user
