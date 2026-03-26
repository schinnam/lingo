"""LingoStalenessJob — flag stale terms and DM their owners.

Algorithm:
1. Find all terms where:
   - is_stale is False (not already notified)
   - last_confirmed_at is older than stale_threshold_days
     (or NULL, treated as created_at falling back to epoch)
2. Mark each as is_stale=True.
3. For each such term that has an owner with a slack_user_id, send a DM.
4. Persist a Job row with progress_json.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from lingo.models.job import Job, JobStatus, JobType
from lingo.models.term import Term
from lingo.models.user import User
from lingo.slack.notifications import send_staleness_dm


async def run_staleness_job(
    *,
    session_factory,
    slack_client,
    stale_threshold_days: int,
) -> None:
    """Run the staleness job and persist a Job record."""
    job = Job(job_type=JobType.staleness, status=JobStatus.running)
    async with session_factory() as sess:
        sess.add(job)
        await sess.commit()
        await sess.refresh(job)
        job_id = job.id

    try:
        terms_flagged, dms_sent = await _flag_and_notify(
            session_factory=session_factory,
            slack_client=slack_client,
            stale_threshold_days=stale_threshold_days,
        )
        async with session_factory() as sess:
            j = await sess.get(Job, job_id)
            j.status = JobStatus.completed
            j.completed_at = datetime.now(timezone.utc)
            j.progress_json = {
                "terms_flagged": terms_flagged,
                "dms_sent": dms_sent,
            }
            await sess.commit()
    except Exception as exc:
        async with session_factory() as sess:
            j = await sess.get(Job, job_id)
            j.status = JobStatus.failed
            j.completed_at = datetime.now(timezone.utc)
            j.error = str(exc)
            await sess.commit()


async def _flag_and_notify(*, session_factory, slack_client, stale_threshold_days: int):
    threshold = datetime.now(timezone.utc) - timedelta(days=stale_threshold_days)

    # Find terms that are NOT already stale and whose last confirmation is old
    async with session_factory() as sess:
        result = await sess.execute(
            select(Term).where(
                Term.is_stale.is_(False),
                Term.last_confirmed_at < threshold,
            )
        )
        stale_terms = result.scalars().all()
        stale_ids = [t.id for t in stale_terms]

        # Mark all as stale in one pass
        for term in stale_terms:
            term.is_stale = True
        await sess.commit()

    terms_flagged = len(stale_ids)
    dms_sent = 0

    # Send DMs for terms that have owners
    for term_id in stale_ids:
        await send_staleness_dm(
            term_id=term_id,
            client=slack_client,
            session_factory=session_factory,
        )
        # Count DM if actually sent (owner exists — checked inside send_staleness_dm)
        async with session_factory() as sess:
            term = await sess.get(Term, term_id)
            if term and term.owner_id:
                owner = await sess.get(User, term.owner_id)
                if owner and owner.slack_user_id:
                    dms_sent += 1

    return terms_flagged, dms_sent
