"""LingoDiscoveryJob — scan Slack history for unrecognised acronyms.

Algorithm:
1. Fetch all public channels.
2. For each channel, fetch messages within the lookback window.
3. Extract tokens matching \\b[A-Z]{2,6}\\b.
4. For each unique acronym not already in the glossary, create a Term
   with status="suggested" and source="slack_discovery".
5. Persist a Job row with progress_json (channels_scanned, terms_found).
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from lingo.models.job import Job, JobStatus, JobType
from lingo.models.term import Term

_ACRONYM_RE = re.compile(r"\b[A-Z]{2,6}\b")


async def run_discovery_job(
    *,
    session_factory,
    slack_client,
    lookback_days: int = 90,
) -> None:
    """Run the discovery job and persist a Job record."""
    job = Job(job_type=JobType.discovery, status=JobStatus.running)
    async with session_factory() as sess:
        sess.add(job)
        await sess.commit()
        await sess.refresh(job)
        job_id = job.id

    try:
        channels_scanned, terms_found = await _scan_slack(
            session_factory=session_factory,
            slack_client=slack_client,
            lookback_days=lookback_days,
        )
        async with session_factory() as sess:
            j = await sess.get(Job, job_id)
            j.status = JobStatus.completed
            j.completed_at = datetime.now(UTC)
            j.progress_json = {
                "channels_scanned": channels_scanned,
                "terms_found": terms_found,
            }
            await sess.commit()
    except Exception as exc:
        async with session_factory() as sess:
            j = await sess.get(Job, job_id)
            j.status = JobStatus.failed
            j.completed_at = datetime.now(UTC)
            j.error = str(exc)
            await sess.commit()


async def _scan_slack(*, session_factory, slack_client, lookback_days: int):
    oldest_ts = (datetime.now(UTC) - timedelta(days=lookback_days)).timestamp()

    # Fetch all channels
    channels_resp = await slack_client.conversations_list()
    channels = channels_resp.get("channels", [])

    # Count acronym occurrences across all channels
    occurrence: Counter = Counter()
    channel_source: dict[str, str] = {}

    for ch in channels:
        ch_id = ch["id"]
        cursor = None
        while True:
            kwargs: dict = {"channel": ch_id, "oldest": str(oldest_ts), "limit": 200}
            if cursor:
                kwargs["cursor"] = cursor
            resp = await slack_client.conversations_history(**kwargs)
            for msg in resp.get("messages", []):
                text = msg.get("text", "")
                for match in _ACRONYM_RE.finditer(text):
                    word = match.group()
                    occurrence[word] += 1
                    if word not in channel_source:
                        channel_source[word] = ch_id
            if not resp.get("has_more"):
                break
            cursor = resp.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

    if not occurrence:
        return len(channels), 0

    # Load existing term names (case-insensitive comparison by uppercasing)
    async with session_factory() as sess:
        result = await sess.execute(select(Term.name))
        existing = {name.upper() for name in result.scalars().all()}

    new_acronyms = [a for a in occurrence if a.upper() not in existing]

    if not new_acronyms:
        return len(channels), 0

    async with session_factory() as sess:
        for acronym in new_acronyms:
            term = Term(
                name=acronym,
                definition="",
                status="suggested",
                source="slack_discovery",
                source_channel_id=channel_source.get(acronym),
                occurrences_count=occurrence[acronym],
            )
            sess.add(term)
        await sess.commit()

    return len(channels), len(new_acronyms)
