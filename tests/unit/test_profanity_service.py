"""Tests for the profanity/content moderation service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from lingo.config import settings
from lingo.services.profanity_service import ProfanityError, check_content


class TestFeatureFlagDisabled:
    async def test_no_check_when_flag_off(self):
        settings.feature_profanity_filter = False
        try:
            await check_content(name="shit", definition="profane content here")
        finally:
            settings.feature_profanity_filter = True


class TestLocalBackend:
    async def test_clean_content_passes(self):
        await check_content(name="API", definition="Application Programming Interface")

    async def test_profane_name_raises(self):
        with pytest.raises(ProfanityError):
            await check_content(name="shit", definition="clean definition")

    async def test_profane_definition_raises(self):
        with pytest.raises(ProfanityError):
            await check_content(name="CleanName", definition="this is bullshit content")

    async def test_error_message_does_not_leak_flagged_word(self):
        with pytest.raises(ProfanityError) as exc_info:
            await check_content(name="ass", definition="clean")
        assert "ass" not in exc_info.value.args[0]

    async def test_error_message_is_user_friendly(self):
        with pytest.raises(ProfanityError) as exc_info:
            await check_content(name="fuck", definition="clean")
        assert "not allowed" in exc_info.value.args[0]


class TestOpenAIBackend:
    async def test_flagged_response_raises(self):
        settings.openai_api_key = "sk-test-key"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": [{"flagged": True}]}
        with patch("lingo.services.profanity_service.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_resp
            )
            with pytest.raises(ProfanityError):
                await check_content(name="badterm", definition="some definition")
        settings.openai_api_key = ""

    async def test_clean_response_passes(self):
        settings.openai_api_key = "sk-test-key"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": [{"flagged": False}]}
        with patch("lingo.services.profanity_service.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_resp
            )
            await check_content(name="API", definition="Application Programming Interface")
        settings.openai_api_key = ""

    async def test_network_failure_falls_back_to_local_clean(self):
        """On network error, clean content still passes via local fallback."""
        settings.openai_api_key = "sk-test-key"
        with patch("lingo.services.profanity_service.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.ConnectError("unreachable")
            )
            await check_content(name="API", definition="Application Programming Interface")
        settings.openai_api_key = ""

    async def test_network_failure_falls_back_to_local_profane(self):
        """On network error, profane content is still caught by local fallback."""
        settings.openai_api_key = "sk-test-key"
        with patch("lingo.services.profanity_service.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.ConnectError("unreachable")
            )
            with pytest.raises(ProfanityError):
                await check_content(name="shit", definition="clean")
        settings.openai_api_key = ""
