"""APScheduler setup for Lingo background jobs.

NOTE: Run the server with --workers 1 (single process) so the scheduler
fires exactly once per trigger.
"""

from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from lingo.config import settings


def create_scheduler(*, session_factory, slack_client) -> AsyncIOScheduler:
    """Create and configure the AsyncIOScheduler with all Lingo jobs.

    The scheduler is *not* started here — call scheduler.start() inside
    the FastAPI lifespan so it shares the running event loop.
    """
    from lingo.scheduler.jobs.discovery import run_discovery_job
    from lingo.scheduler.jobs.staleness import run_staleness_job

    scheduler = AsyncIOScheduler()

    if settings.feature_discovery:
        scheduler.add_job(
            run_discovery_job,
            trigger="cron",
            hour=2,  # 2 AM daily
            id="discovery_job",
            kwargs={
                "session_factory": session_factory,
                "slack_client": slack_client,
                "lookback_days": 90,
            },
        )

    if settings.feature_staleness:
        scheduler.add_job(
            run_staleness_job,
            trigger="cron",
            day_of_week="mon",
            hour=3,  # 3 AM every Monday
            id="staleness_job",
            kwargs={
                "session_factory": session_factory,
                "slack_client": slack_client,
                "stale_threshold_days": settings.stale_threshold_days,
            },
        )

    return scheduler
