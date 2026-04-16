"""REST routes for /api/v1/tokens."""

import base64
import hashlib
import os
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from lingo.api.deps import CurrentUser, SessionDep
from lingo.api.schemas import TokenCreate, TokenCreateResponse, TokenResponse
from lingo.models.token import Token
from lingo.services.audit_service import AuditService

router = APIRouter(prefix="/api/v1/tokens", tags=["tokens"])


def _generate_token() -> tuple[str, str]:
    """Return (raw_token, token_hash). Raw token shown once; hash stored."""
    raw = base64.urlsafe_b64encode(os.urandom(32)).decode("ascii").rstrip("=")
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, token_hash


@router.get("", response_model=list[TokenResponse])
async def list_tokens(session: SessionDep, current_user: CurrentUser):
    result = await session.execute(
        select(Token).where(Token.user_id == current_user.id, Token.revoked_at.is_(None))
    )
    return list(result.scalars().all())


@router.post("", status_code=201, response_model=TokenCreateResponse)
async def create_token(body: TokenCreate, session: SessionDep, current_user: CurrentUser):
    raw, token_hash = _generate_token()
    token = Token(
        user_id=current_user.id,
        name=body.name,
        token_hash=token_hash,
        scopes=body.scopes,
    )
    session.add(token)
    await session.commit()
    await session.refresh(token)
    await AuditService(session).log(
        "token.created",
        actor_id=current_user.id,
        target_type="token",
        target_id=token.id,
        payload={"name": token.name, "scopes": token.scopes},
    )
    return TokenCreateResponse(
        id=token.id,
        name=token.name,
        scopes=token.scopes,
        user_id=token.user_id,
        token=raw,
    )


@router.delete("/{token_id}", status_code=204)
async def delete_token(token_id: UUID, session: SessionDep, current_user: CurrentUser):
    token = await session.get(Token, token_id)
    if token is None:
        raise HTTPException(status_code=404, detail="Token not found")
    if token.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your token")
    token_name = token.name
    await session.delete(token)
    await session.commit()
    await AuditService(session).log(
        "token.revoked",
        actor_id=current_user.id,
        target_type="token",
        target_id=token_id,
        payload={"name": token_name},
    )
