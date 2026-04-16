"""ASGI middleware that enforces API Bearer token auth on the MCP endpoint.

Validates against the Token table using the same sha256-hash lookup
used by the REST API bearer auth. Returns 401 JSON on failure.
"""

import hashlib
import json

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from lingo.db.session import SessionFactory


class MCPBearerAuthMiddleware:
    """Starlette middleware: require a valid API Bearer token for all requests."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            request = Request(scope, receive)
            auth_header = request.headers.get("authorization", "")
            raw_token = self._parse_bearer(auth_header)
            if raw_token is None or not await self._is_valid_token(raw_token):
                response = Response(
                    content=json.dumps({"detail": "Not authenticated"}),
                    status_code=401,
                    media_type="application/json",
                )
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)

    @staticmethod
    def _parse_bearer(authorization: str) -> str | None:
        parts = authorization.split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        return parts[1]

    @staticmethod
    async def _is_valid_token(raw_token: str) -> bool:
        from sqlalchemy import select

        from lingo.models import User
        from lingo.models.token import Token

        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        async with SessionFactory() as session:
            result = await session.execute(
                select(Token).where(
                    Token.token_hash == token_hash,
                    Token.revoked_at.is_(None),
                )
            )
            token = result.scalar_one_or_none()
            if token is None:
                return False
            user = await session.get(User, token.user_id)
            return user is not None and user.is_active
