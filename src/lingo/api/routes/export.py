"""REST routes for /api/v1/export."""
from fastapi import APIRouter, Query
from fastapi.responses import Response
from sqlalchemy import select

from lingo.api.deps import SessionDep
from lingo.models.term import Term

router = APIRouter(prefix="/api/v1", tags=["export"])


@router.get("/export")
async def export_terms(
    session: SessionDep,
    status: str = Query("official"),
    format: str = Query("markdown"),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    stmt = (
        select(Term)
        .where(Term.status == status)
        .order_by(Term.name)
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    terms = list(result.scalars().all())

    lines = [f"# Lingo Glossary\n"]
    for term in terms:
        lines.append(f"## {term.name}")
        if term.full_name:
            lines.append(f"**{term.full_name}**\n")
        lines.append(f"{term.definition}\n")
        if term.category:
            lines.append(f"_Category: {term.category}_\n")
        lines.append("")

    content = "\n".join(lines)
    return Response(content=content, media_type="text/markdown")
