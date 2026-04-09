"""Auth routes: Slack OIDC login/callback, dev login, logout, /me."""
import hmac
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lingo.auth.slack_oidc import (
    AuthError,
    build_auth_url,
    exchange_code,
    get_user_info,
    hmac_sign,
    upsert_user,
)
from lingo.config import settings
from lingo.db.session import get_session
from lingo.models import User

router = APIRouter(tags=["auth"])

_STATE_COOKIE = "lingo_oauth_state"


@router.get("/auth/slack/login")
async def slack_login():
    nonce = secrets.token_urlsafe(32)
    state = hmac_sign(nonce, settings.secret_key)
    redirect_url = build_auth_url(state=state)
    response = RedirectResponse(url=redirect_url)
    response.set_cookie(
        key=_STATE_COOKIE,
        value=nonce,
        max_age=300,
        httponly=True,
        samesite="lax",
        secure=not settings.dev_mode,
    )
    return response


@router.get("/auth/slack/callback")
async def slack_callback(
    request: Request,
    code: str,
    state: str,
    session: AsyncSession = Depends(get_session),
):
    cookie_nonce = request.cookies.get(_STATE_COOKIE)
    if not cookie_nonce:
        raise HTTPException(status_code=400, detail="Missing OAuth state cookie")

    expected = hmac_sign(cookie_nonce, settings.secret_key)
    if not hmac.compare_digest(expected, state):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    try:
        token_data = await exchange_code(code)
        user_info = await get_user_info(token_data["access_token"])
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=exc.code)

    user = await upsert_user(
        slack_user_id=user_info["sub"],
        email=user_info["email"],
        display_name=user_info.get("name", ""),
        session=session,
    )
    request.session["user_id"] = str(user.id)

    response = RedirectResponse(url="/")
    response.delete_cookie(_STATE_COOKIE)
    return response


@router.get("/auth/dev/login")
async def dev_login(
    request: Request,
    email: str,
    session: AsyncSession = Depends(get_session),
):
    if not settings.dev_mode:
        raise HTTPException(status_code=404, detail="Not found")

    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(email=email, role="member")
        session.add(user)
        await session.commit()
        await session.refresh(user)

    request.session["user_id"] = str(user.id)
    return RedirectResponse(url="/")


@router.post("/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/auth/me")
async def auth_me(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    user_id_str = request.session.get("user_id")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await session.get(User, user_uuid)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "slack_user_id": user.slack_user_id,
    }
