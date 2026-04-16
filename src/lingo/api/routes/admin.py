"""REST routes for /api/v1/admin."""
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from lingo.api.deps import AdminUser, SessionDep
from lingo.api.schemas import AuditEventResponse, JobResponse, StatsResponse
from lingo.models.job import Job, JobType
from lingo.models.term import Term
from lingo.models.user import User
from lingo.models.vote import Vote
from lingo.services.audit_service import AuditService

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

VALID_JOB_TYPES = {jt.value for jt in JobType}


@router.get("/stats", response_model=StatsResponse)
async def get_stats(session: SessionDep, admin: AdminUser):
    total_terms_result = await session.execute(select(func.count()).select_from(Term))
    total_terms = total_terms_result.scalar() or 0

    status_counts = {}
    for status in ("pending", "community", "official", "suggested"):
        result = await session.execute(
            select(func.count()).select_from(Term).where(Term.status == status)
        )
        status_counts[status] = result.scalar() or 0

    total_users_result = await session.execute(select(func.count()).select_from(User))
    total_users = total_users_result.scalar() or 0

    total_votes_result = await session.execute(select(func.count()).select_from(Vote))
    total_votes = total_votes_result.scalar() or 0

    return StatsResponse(
        total_terms=total_terms,
        by_status=status_counts,
        total_users=total_users,
        total_votes=total_votes,
    )


@router.get("/jobs", response_model=list[JobResponse])
async def list_jobs(session: SessionDep, admin: AdminUser):
    result = await session.execute(select(Job).order_by(Job.started_at.desc()))
    return list(result.scalars().all())


@router.get("/audit", response_model=list[AuditEventResponse])
async def list_audit_events(
    session: SessionDep,
    admin: AdminUser,
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    svc = AuditService(session)
    return await svc.list(limit=limit, offset=offset)


@router.post("/jobs/{job_type}/run", status_code=202, response_model=JobResponse)
async def run_job(job_type: str, session: SessionDep, admin: AdminUser):
    if job_type not in VALID_JOB_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid job type '{job_type}'. Valid types: {sorted(VALID_JOB_TYPES)}",
        )
    job = Job(job_type=JobType(job_type))
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job
