"""REST routes for /api/v1/terms."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from lingo.api.deps import CurrentUser, SessionDep
from lingo.api.schemas import TermCreate, TermResponse, TermUpdate, VoteResponse
from lingo.models.vote import Vote
from lingo.services.term_service import TermNotFoundError, TermService, VersionConflictError
from lingo.services.vote_service import AlreadyVotedError, VoteService
from lingo.config import settings

router = APIRouter(prefix="/api/v1/terms", tags=["terms"])


def _term_to_response(term, vote_count: int = 0) -> TermResponse:
    return TermResponse(
        id=term.id,
        name=term.name,
        full_name=term.full_name,
        definition=term.definition,
        category=term.category,
        status=term.status,
        source=term.source,
        is_stale=term.is_stale,
        version=term.version,
        vote_count=vote_count,
    )


async def _count_votes(session, term_id) -> int:
    result = await session.execute(
        select(func.count()).select_from(Vote).where(Vote.term_id == term_id)
    )
    return result.scalar() or 0


@router.post("", status_code=201, response_model=TermResponse)
async def create_term(
    body: TermCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    svc = TermService(session)
    term = await svc.create(
        name=body.name,
        definition=body.definition,
        full_name=body.full_name,
        category=body.category,
        created_by=current_user.id,
    )
    return _term_to_response(term)


@router.get("", response_model=list[TermResponse])
async def list_terms(
    session: SessionDep,
    q: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    svc = TermService(session)
    terms = await svc.list(q=q, status=status, category=category, limit=limit, offset=offset)
    results = []
    for t in terms:
        vc = await _count_votes(session, t.id)
        results.append(_term_to_response(t, vc))
    return results


@router.get("/{term_id}", response_model=TermResponse)
async def get_term(term_id: UUID, session: SessionDep):
    svc = TermService(session)
    try:
        term = await svc.get(term_id)
    except TermNotFoundError:
        raise HTTPException(status_code=404, detail="Term not found")
    vc = await _count_votes(session, term.id)
    return _term_to_response(term, vc)


@router.put("/{term_id}", response_model=TermResponse)
async def update_term(
    term_id: UUID,
    body: TermUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    svc = TermService(session)
    try:
        term = await svc.update(
            term_id=term_id,
            version=body.version,
            updated_by=current_user.id,
            definition=body.definition,
            full_name=body.full_name,
            category=body.category,
            change_note=body.change_note,
        )
    except TermNotFoundError:
        raise HTTPException(status_code=404, detail="Term not found")
    except VersionConflictError:
        raise HTTPException(status_code=409, detail="Version conflict")
    vc = await _count_votes(session, term.id)
    return _term_to_response(term, vc)


@router.delete("/{term_id}", status_code=204)
async def delete_term(
    term_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
):
    svc = TermService(session)
    try:
        await svc.delete(term_id)
    except TermNotFoundError:
        raise HTTPException(status_code=404, detail="Term not found")


@router.post("/{term_id}/vote", response_model=VoteResponse)
async def vote_term(
    term_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
):
    vote_svc = VoteService(
        session,
        community_threshold=settings.community_threshold,
        official_threshold=settings.official_threshold,
    )
    try:
        result = await vote_svc.vote(term_id=term_id, user_id=current_user.id)
    except TermNotFoundError:
        raise HTTPException(status_code=404, detail="Term not found")
    except AlreadyVotedError:
        raise HTTPException(status_code=409, detail="Already voted")
    return VoteResponse(
        vote_count=result.vote_count,
        transition=result.transition.value if result.transition else None,
    )
