"""Profanity / content moderation service.

Backend selection (evaluated at call time):
  - settings.openai_api_key non-empty  → OpenAI Moderation API (async, free)
  - otherwise                          → better-profanity (local wordlist, no API key)

On OpenAI network failure, falls back to the local backend so availability
issues never hard-block term creation.
"""

from __future__ import annotations

import asyncio

import httpx
from better_profanity import profanity

from lingo.config import settings

profanity.load_censor_words()


class ProfanityError(Exception):
    """Raised when submitted content fails the profanity/abuse check."""


async def _check_local(text: str) -> bool:
    return await asyncio.to_thread(profanity.contains_profanity, text)


async def _check_openai(text: str, api_key: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/moderations",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"input": text},
            )
            resp.raise_for_status()
            return resp.json()["results"][0]["flagged"]
    except httpx.HTTPError:
        return await _check_local(text)


async def check_content(name: str, definition: str) -> None:
    """Check name and definition for profanity/abusive content.

    Raises ProfanityError if either field is flagged.
    Does nothing when the feature flag is disabled.
    """
    if not settings.feature_profanity_filter:
        return

    api_key = settings.openai_api_key
    if api_key:
        checker = lambda text: _check_openai(text, api_key)  # noqa: E731
    else:
        checker = _check_local

    for text in (name, definition):
        if await checker(text):
            raise ProfanityError(
                "Your submission contains content that is not allowed. "
                "Please review the term name and definition."
            )
