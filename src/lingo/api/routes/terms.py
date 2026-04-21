"""REST routes for /api/v1/terms."""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Body, HTTPException, Query, Request
from sqlalchemy import func, select

from lingo.api.deps import AdminUser, CurrentUser, EditorUser, SessionDep, require_feature
from lingo.api.schemas import (
    AcceptSuggestionRequest,
    HistoryResponse,
    RelationshipCreate,
    RelationshipResponse,
    SuggestionRequest,
    SuggestionResponse,
    TermCreate,
    TermResponse,
    TermsListResponse,
    TermUpdate,
    VoteResponse,
)
from lingo.config import settings
from lingo.models.term import Term as TermModel
from lingo.models.vote import Vote
from lingo.services.audit_service import AuditService
from lingo.services.term_service import (
    AlreadyOwnedError,
    InvalidStatusTransitionError,
    ProfanityError,
    RelationshipNotFoundError,
    ReservedNameError,
    SuggestionNotFoundError,
    TermNotFoundError,
    TermService,
    TooManyDefinitionsError,
    VersionConflictError,
)
from lingo.services.vote_service import AlreadyVotedError, VoteService
from lingo.slack.notifications import send_suggestion_dm

router = APIRouter(prefix="/api/v1/terms", tags=["terms"])


async def _term_to_response(
    term, vote_count: int = 0, extra_definitions: list[str] | None = None
) -> TermResponse:
    return TermResponse(
        id=term.id,
        name=term.name,
        full_name=term.full_name,
        definition=term.definition,
        extra_definitions=extra_definitions or [],
        category=term.category,
        status=term.status,
        source=term.source,
        is_stale=term.is_stale,
        version=term.version,
        vote_count=vote_count,
        owner_id=term.owner_id,
    )


async def _count_votes(session, term_id) -> int:
    result = await session.execute(
        select(func.count()).select_from(Vote).where(Vote.term_id == term_id)
    )
    return result.scalar() or 0


async def _build_term_response(svc: TermService, session, term) -> TermResponse:
    vc = await _count_votes(session, term.id)
    extras = await svc.get_extra_definitions(term.id)
    extra_defs = [e.definition for e in extras]
    return await _term_to_response(term, vc, extra_defs)


@router.post("", status_code=201, response_model=TermResponse)
async def create_term(
    body: TermCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    svc = TermService(session)
    try:
        term = await svc.create(
            name=body.name,
            definition=body.definition,
            full_name=body.full_name,
            category=body.category,
            created_by=current_user.id,
        )
    except ReservedNameError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except ProfanityError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    await AuditService(session).log(
        "term.created",
        actor_id=current_user.id,
        target_type="term",
        target_id=term.id,
        payload={"name": term.name},
    )
    return await _build_term_response(svc, session, term)


@router.get("", response_model=TermsListResponse)
async def list_terms(
    session: SessionDep,
    q: str | None = Query(None),
    status: str | None = Query(None),
    category: str | None = Query(None),
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
        select(TermModel.status, func.count()).select_from(TermModel).group_by(TermModel.status)
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
        results.append(await _build_term_response(svc, session, t))
    return TermsListResponse(
        items=results, total=total, offset=offset, limit=limit, counts_by_status=counts_by_status
    )


@router.get("/{term_id}", response_model=TermResponse)
async def get_term(term_id: UUID, session: SessionDep):
    svc = TermService(session)
    try:
        term = await svc.get(term_id)
    except TermNotFoundError:
        raise HTTPException(status_code=404, detail="Term not found")
    return await _build_term_response(svc, session, term)


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
    return await _build_term_response(svc, session, term)


@router.delete("/{term_id}", status_code=204)
async def delete_term(
    term_id: UUID,
    session: SessionDep,
    current_user: AdminUser,
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


@router.post(
    "/{term_id}/vote", response_model=VoteResponse, dependencies=[require_feature("voting")]
)
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


@router.post("/{term_id}/suggest", status_code=201, response_model=SuggestionResponse)
async def suggest_definition(
    term_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    current_user: CurrentUser,
    body: SuggestionRequest = Body(...),
):
    """Submit a suggested definition change. Notifies the owner via Slack DM."""
    svc = TermService(session)
    try:
        suggestion = await svc.suggest_definition(
            term_id=term_id,
            definition=body.definition,
            comment=body.comment,
            by_user=current_user.id,
        )
    except TermNotFoundError:
        raise HTTPException(status_code=404, detail="Term not found")

    slack_client = getattr(request.app.state, "slack_client", None)
    if slack_client is not None:
        from lingo.db.session import SessionFactory

        background_tasks.add_task(
            send_suggestion_dm,
            term_id=term_id,
            suggester_name=current_user.display_name or current_user.email,
            suggested_definition=body.definition,
            comment=body.comment or "",
            client=slack_client,
            session_factory=SessionFactory,
        )

    return suggestion


@router.get("/{term_id}/suggestions", response_model=list[SuggestionResponse])
async def list_suggestions(
    term_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    status: str | None = Query("pending"),
):
    """List definition suggestions for a term. Accessible to the term owner or editors/admins."""
    svc = TermService(session)
    try:
        term = await svc.get(term_id)
    except TermNotFoundError:
        raise HTTPException(status_code=404, detail="Term not found")

    is_owner = term.owner_id is not None and term.owner_id == current_user.id
    is_privileged = current_user.role in ("editor", "admin")
    if not is_owner and not is_privileged:
        raise HTTPException(
            status_code=403, detail="Only the term owner or editors can view suggestions"
        )

    return await svc.get_suggestions(term_id, status=status)


@router.post("/{term_id}/suggestions/{suggestion_id}/accept", response_model=TermResponse)
async def accept_suggestion(
    term_id: UUID,
    suggestion_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    body: AcceptSuggestionRequest = Body(default=AcceptSuggestionRequest()),
    replace: bool = Query(False),
):
    """Accept a suggested definition. Owner or editor only.

    Three modes (checked in order):
    - body.merged_definition provided → owner's hand-edited text replaces the primary definition
    - replace=true → suggestion text replaces the primary definition verbatim
    - default → suggestion added as an extra definition (max 3 total)
    """
    svc = TermService(session)
    try:
        term = await svc.get(term_id)
    except TermNotFoundError:
        raise HTTPException(status_code=404, detail="Term not found")

    is_owner = term.owner_id is not None and term.owner_id == current_user.id
    is_privileged = current_user.role in ("editor", "admin")
    if not is_owner and not is_privileged:
        raise HTTPException(
            status_code=403, detail="Only the term owner or editors can accept suggestions"
        )

    try:
        term = await svc.accept_suggestion(
            term_id=term_id,
            suggestion_id=suggestion_id,
            by_user=current_user.id,
            replace=replace,
            merged_definition=body.merged_definition,
        )
    except SuggestionNotFoundError:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    except TooManyDefinitionsError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return await _build_term_response(svc, session, term)


@router.post("/{term_id}/suggestions/{suggestion_id}/reject", status_code=204)
async def reject_suggestion(
    term_id: UUID,
    suggestion_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
):
    """Reject a suggested definition. Owner or editor only."""
    svc = TermService(session)
    try:
        term = await svc.get(term_id)
    except TermNotFoundError:
        raise HTTPException(status_code=404, detail="Term not found")

    is_owner = term.owner_id is not None and term.owner_id == current_user.id
    is_privileged = current_user.role in ("editor", "admin")
    if not is_owner and not is_privileged:
        raise HTTPException(
            status_code=403, detail="Only the term owner or editors can reject suggestions"
        )

    try:
        await svc.reject_suggestion(
            term_id=term_id,
            suggestion_id=suggestion_id,
            by_user=current_user.id,
        )
    except SuggestionNotFoundError:
        raise HTTPException(status_code=404, detail="Suggestion not found")


@router.post(
    "/{term_id}/official", response_model=TermResponse, dependencies=[require_feature("voting")]
)
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
    return await _build_term_response(svc, session, term)


@router.post(
    "/{term_id}/confirm",
    response_model=TermResponse,
    dependencies=[require_feature("staleness")],
)
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
    return await _build_term_response(svc, session, term)


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
    return await _build_term_response(svc, session, term)


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
    return await _build_term_response(svc, session, term)


@router.post(
    "/{term_id}/relationships",
    status_code=201,
    response_model=RelationshipResponse,
    dependencies=[require_feature("relationships")],
)
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


@router.delete(
    "/{term_id}/relationships/{rel_id}",
    status_code=204,
    dependencies=[require_feature("relationships")],
)
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


@router.post(
    "/{term_id}/promote", response_model=TermResponse, dependencies=[require_feature("voting")]
)
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
    return await _build_term_response(svc, session, term)


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
