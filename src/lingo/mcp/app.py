"""FastMCP application with Lingo glossary tools.

Tools exposed:
  get_term(name)                                     → term details or error
  search_terms(query, status?, limit?)               → matching terms
  list_terms(category?, status?, limit?, offset?)    → paginated term list
"""

import fastmcp
from sqlalchemy import select

from lingo.db.session import SessionFactory as async_session_factory
from lingo.models.term import Term

mcp = fastmcp.FastMCP(
    name="Lingo",
    instructions="Company glossary — look up, search, and list internal terms and acronyms.",
)


def _term_to_text(term: Term) -> str:
    """Render a term as a readable text block."""
    parts = [f"**{term.name}**"]
    if term.full_name:
        parts.append(f" ({term.full_name})")
    parts.append(f"\n{term.definition}")
    parts.append(f"\nStatus: {term.status}")
    if term.category:
        parts.append(f" | Category: {term.category}")
    return "".join(parts)


@mcp.tool()
async def get_term(name: str) -> str:
    """Look up a term by exact name (case-insensitive).

    Args:
        name: The term or acronym to look up (e.g. "API", "CI/CD").

    Returns:
        Term definition and metadata, or an error message if not found.
    """
    async with async_session_factory() as session:
        result = await session.execute(select(Term).where(Term.name.ilike(name)))
        term = result.scalar_one_or_none()

    if term is None:
        return f"Term '{name}' not found in the glossary."
    return _term_to_text(term)


@mcp.tool()
async def search_terms(
    query: str,
    status: str | None = None,
    limit: int = 10,
) -> str:
    """Search for terms by keyword in name, definition, or full name.

    Args:
        query: Search text (matches name, definition, full_name).
        status: Filter by status — one of: pending, official, suggested. Optional.
        limit: Maximum number of results to return (default 10, max 50).

    Returns:
        Matching terms as formatted text, or a 'no results' message.
    """
    limit = min(limit, 50)

    async with async_session_factory() as session:
        stmt = select(Term)
        if query:
            pattern = f"%{query}%"
            stmt = stmt.where(
                Term.name.ilike(pattern)
                | Term.definition.ilike(pattern)
                | Term.full_name.ilike(pattern)
            )
        if status:
            stmt = stmt.where(Term.status == status)
        stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        terms = list(result.scalars().all())

    if not terms:
        return f"No terms found matching '{query}'."
    return "\n\n".join(_term_to_text(t) for t in terms)


@mcp.tool()
async def list_terms(
    category: str | None = None,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> str:
    """List glossary terms with optional filters.

    Args:
        category: Filter by category (e.g. "tech", "business"). Optional.
        status: Filter by status — one of: pending, official, suggested. Optional.
        limit: Page size (default 20, max 100).
        offset: Pagination offset (default 0).

    Returns:
        Formatted list of terms.
    """
    limit = min(limit, 100)

    async with async_session_factory() as session:
        stmt = select(Term)
        if category:
            stmt = stmt.where(Term.category == category)
        if status:
            stmt = stmt.where(Term.status == status)
        stmt = stmt.offset(offset).limit(limit)
        result = await session.execute(stmt)
        terms = list(result.scalars().all())

    if not terms:
        return "No terms found."
    return "\n\n".join(_term_to_text(t) for t in terms)
