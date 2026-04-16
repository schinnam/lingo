"""REST routes for /api/v1/export."""

from fastapi import APIRouter, Query
from fastapi.responses import Response
from sqlalchemy import select

from lingo.api.deps import CurrentUser, SessionDep
from lingo.models.term import Term

router = APIRouter(prefix="/api/v1", tags=["export"])

_PAGE_CAP = 500


@router.get("/export")
async def export_terms(
    session: SessionDep,
    current_user: CurrentUser,
    status: str = Query("official"),
    format: str = Query("markdown"),
    limit: int = Query(_PAGE_CAP, le=_PAGE_CAP),
    offset: int = Query(0),
):
    # Fetch one extra to detect truncation without a separate COUNT query
    stmt = (
        select(Term)
        .where(Term.status == status)
        .order_by(Term.name)
        .offset(offset)
        .limit(limit + 1)
    )
    result = await session.execute(stmt)
    rows = list(result.scalars().all())

    truncated = len(rows) > limit
    terms = rows[:limit]

    lines = ["# Lingo Glossary\n"]
    for term in terms:
        lines.append(f"## {term.name}")
        if term.full_name:
            lines.append(f"**{term.full_name}**\n")
        lines.append(f"{term.definition}\n")
        if term.category:
            lines.append(f"_Category: {term.category}_\n")
        lines.append("")

    content = "\n".join(lines)
    headers = {"Lingo-Truncated": "true"} if truncated else {}
    return Response(content=content, media_type="text/markdown", headers=headers)
