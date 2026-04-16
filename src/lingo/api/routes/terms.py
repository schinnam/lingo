"""REST routes for /api/v1/terms."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Body, HTTPException, Query, Request
from sqlalchemy import func, select

from lingo.api.deps import CurrentUser, EditorUser, SessionDep, require_feature
from lingo.api.schemas import (
    DisputeRequest,
    HistoryResponse,
    RelationshipCreate,
    RelationshipResponse,
    TermCreate,
    TermResponse,
    TermsListResponse,
    TermUpdate,
    VoteResponse,
)
from lingo.slack.notifications import send_dispute_dm
from lingo.models.vote import Vote
from lingo.models.term import Term as TermModel
from lingo.services.term_service import (
    AlreadyOwnedError,
    InvalidStatusTransitionError,
    RelationshipNotFoundError,
    TermNotFoundError,
    TermService,
    VersionConflictError,
)
from lingo.services.vote_service import AlreadyVotedError, VoteService
from lingo.services.audit_service import AuditService
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
        is_disputed=term.is_disputed,
        version=term.version,
        vote_count=vote_count,
        owner_id=term.owner_id,
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
    await AuditService(session).log(
        "term.created",
        actor_id=current_user.id,
        target_type="term",
        target_id=term.id,
        payload={"name": term.name},
    )
    return _term_to_response(term)


@router.get("", response_model=TermsListResponse)
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
    # Count total matching rows (without pagination)
    count_stmt = select(func.count()).select_from(TermModel)
    if status is not None:
        count_stmt = count_stmt.where(TermModel.status == status)
    if category is not None:
        count_stmt = count_stmt.where(TermModel.category == category)
    if q is not None:
        pattern = f"%{q}%"
        count_stmt = count_stmt.where(
            TermModel.name.ilike(pattern)
            | TermModel.definition.ilike(pattern)
            | TermModel.full_name.ilike(pattern)
        )
    total = (await session.execute(count_stmt)).scalar() or 0
    # Per-status counts (filtered by q/category but not by status)
    status_count_stmt = (
        select(TermModel.status, func.count())
        .select_from(TermModel)
        .group_by(TermModel.status)
    )
    if category is not None:
        status_count_stmt = status_count_stmt.where(TermModel.category == category)
    if q is not None:
        pattern = f"%{q}%"
        status_count_stmt = status_count_stmt.where(
            TermModel.name.ilike(pattern)
            | TermModel.definition.ilike(pattern)
            | TermModel.full_name.ilike(pattern)
        )
    counts_by_status = {str(k): v for k, v in (await session.execute(status_count_stmt)).all()}
    results = []
    for t in terms:
        vc = await _count_votes(session, t.id)
        results.append(_term_to_response(t, vc))
    return TermsListResponse(items=results, total=total, offset=offset, limit=limit, counts_by_status=counts_by_status)


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
    await AuditService(session).log(
        "term.updated",
        actor_id=current_user.id,
        target_type="term",
        target_id=term.id,
        payload={"name": term.name, "change_note": body.change_note},
    )
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
        term = await svc.get(term_id)
        term_name = term.name
        await svc.delete(term_id)
    except TermNotFoundError:
        raise HTTPException(status_code=404, detail="Term not found")
    await AuditService(session).log(
        "term.deleted",
        actor_id=current_user.id,
        target_type="term",
        target_id=term_id,
        payload={"name": term_name},
    )


@router.post("/{term_id}/vote", response_model=VoteResponse, dependencies=[require_feature("voting")])
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
    await AuditService(session).log(
        "vote.cast",
        actor_id=current_user.id,
        target_type="term",
        target_id=term_id,
        payload={"transition": result.transition.value if result.transition else None},
    )
    return VoteResponse(
        vote_count=result.vote_count,
        transition=result.transition.value if result.transition else None,
    )


@router.post("/{term_id}/dispute", response_model=TermResponse)
async def dispute_term(
    term_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    current_user: CurrentUser,
    body: DisputeRequest = Body(default=DisputeRequest()),
):
    """Flag a term as disputed. Records the dispute and notifies the owner via Slack DM."""
    svc = TermService(session)
    try:
        term = await svc.dispute(term_id=term_id, by_user=current_user.id, comment=body.comment or "")
    except TermNotFoundError:
        raise HTTPException(status_code=404, detail="Term not found")

    slack_client = getattr(request.app.state, "slack_client", None)
    if slack_client is not None:
        from lingo.db.session import SessionFactory
        background_tasks.add_task(
            send_dispute_dm,
            term_id=term.id,
            disputer_name=current_user.display_name or current_user.email,
            reason=body.comment or "No reason given",
            client=slack_client,
            session_factory=SessionFactory,
        )

    vc = await _count_votes(session, term.id)
    return _term_to_response(term, vc)


@router.post("/{term_id}/official", response_model=TermResponse, dependencies=[require_feature("voting")])
async def mark_official(
    term_id: UUID,
    session: SessionDep,
    editor: EditorUser,
):
    svc = TermService(session)
    try:
        term = await svc.mark_official(term_id=term_id, by_user=editor.id)
    except TermNotFoundError:
        raise HTTPException(status_code=404, detail="Term not found")
    await AuditService(session).log(
        "term.official",
        actor_id=editor.id,
        target_type="term",
        target_id=term.id,
        payload={"name": term.name},
    )
    vc = await _count_votes(session, term.id)
    return _term_to_response(term, vc)


@router.post("/{term_id}/confirm", response_model=TermResponse, dependencies=[require_feature("staleness")])
async def confirm_term(
    term_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
):
    svc = TermService(session)
    try:
        term = await svc.confirm(term_id=term_id, by_user=current_user.id)
    except TermNotFoundError:
        raise HTTPException(status_code=404, detail="Term not found")
    vc = await _count_votes(session, term.id)
    return _term_to_response(term, vc)


@router.post("/{term_id}/claim", response_model=TermResponse)
async def claim_term(
    term_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
):
    svc = TermService(session)
    force = current_user.role in ("editor", "admin")
    try:
        term = await svc.claim(term_id=term_id, user_id=current_user.id, force=force)
    except TermNotFoundError:
        raise HTTPException(status_code=404, detail="Term not found")
    except AlreadyOwnedError:
        raise HTTPException(status_code=409, detail="Term already has an owner")
    vc = await _count_votes(session, term.id)
    return _term_to_response(term, vc)


@router.get("/{term_id}/history", response_model=list[HistoryResponse])
async def get_history(
    term_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
):
    svc = TermService(session)
    try:
        history = await svc.get_history(term_id)
    except TermNotFoundError:
        raise HTTPException(status_code=404, detail="Term not found")
    return history


@router.post("/{term_id}/revert/{history_id}", response_model=TermResponse)
async def revert_term(
    term_id: UUID,
    history_id: UUID,
    session: SessionDep,
    editor: EditorUser,
):
    svc = TermService(session)
    try:
        term = await svc.revert(term_id=term_id, history_id=history_id, by_user=editor.id)
    except TermNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    vc = await _count_votes(session, term.id)
    return _term_to_response(term, vc)


@router.post("/{term_id}/relationships", status_code=201, response_model=RelationshipResponse, dependencies=[require_feature("relationships")])
async def add_relationship(
    term_id: UUID,
    body: RelationshipCreate,
    session: SessionDep,
    editor: EditorUser,
):
    svc = TermService(session)
    try:
        rel = await svc.add_relationship(
            term_id=term_id,
            related_term_id=body.related_term_id,
            relationship_type=body.relationship_type,
            created_by=editor.id,
        )
    except TermNotFoundError:
        raise HTTPException(status_code=404, detail="Term not found")
    return rel


@router.delete("/{term_id}/relationships/{rel_id}", status_code=204, dependencies=[require_feature("relationships")])
async def delete_relationship(
    term_id: UUID,
    rel_id: UUID,
    session: SessionDep,
    editor: EditorUser,
):
    svc = TermService(session)
    try:
        await svc.delete_relationship(term_id=term_id, rel_id=rel_id)
    except RelationshipNotFoundError:
        raise HTTPException(status_code=404, detail="Relationship not found")


@router.post("/{term_id}/promote", response_model=TermResponse, dependencies=[require_feature("voting")])
async def promote_term(
    term_id: UUID,
    session: SessionDep,
    editor: EditorUser,
):
    svc = TermService(session)
    try:
        term = await svc.promote(term_id=term_id, by_user=editor.id)
    except TermNotFoundError:
        raise HTTPException(status_code=404, detail="Term not found")
    except InvalidStatusTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    vc = await _count_votes(session, term.id)
    return _term_to_response(term, vc)


@router.post("/{term_id}/dismiss", status_code=204, dependencies=[require_feature("voting")])
async def dismiss_term(
    term_id: UUID,
    session: SessionDep,
    editor: EditorUser,
):
    svc = TermService(session)
    try:
        await svc.dismiss(term_id=term_id, by_user=editor.id)
    except TermNotFoundError:
        raise HTTPException(status_code=404, detail="Term not found")
