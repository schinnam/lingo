"""Tests for CORS middleware configuration."""
import pytest
from httpx import AsyncClient, ASGITransport

from lingo.main import app
from lingo.config import settings


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


class TestCORSMiddleware:
    async def test_preflight_returns_allow_origin(self, client: AsyncClient):
        """OPTIONS preflight should return Access-Control-Allow-Origin matching app_url."""
        response = await client.options(
            "/health",
            headers={
                "Origin": settings.app_url,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-origin") == settings.app_url

    async def test_regular_request_returns_allow_origin(self, client: AsyncClient):
        """Cross-origin GET should return Access-Control-Allow-Origin matching app_url."""
        response = await client.get(
            "/health",
            headers={"Origin": settings.app_url},
        )
        assert response.headers.get("access-control-allow-origin") == settings.app_url

    async def test_unknown_origin_not_allowed(self, client: AsyncClient):
        """Requests from an unknown origin should not get CORS headers."""
        response = await client.get(
            "/health",
            headers={"Origin": "https://evil.example.com"},
        )
        assert response.headers.get("access-control-allow-origin") is None
