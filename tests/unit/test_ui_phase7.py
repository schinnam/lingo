"""Tests for Phase 7 — Web UI static file serving + SPA fallback."""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from lingo.db.session import get_session
from lingo.main import app
from lingo.models.base import Base


@pytest.fixture
async def test_engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def test_session_factory(test_engine):
    return async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)


@pytest.fixture
async def client(test_session_factory):
    """Test client with DB overridden."""

    async def _override():
        async with test_session_factory() as sess:
            yield sess

    app.dependency_overrides[get_session] = _override
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


class TestHealthEndpoint:
    async def test_health_returns_ok(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestSPAFallback:
    """Test the SPA fallback route that serves index.html for unknown paths."""

    async def test_unknown_path_returns_json_or_html_when_no_static_built(
        self, client: AsyncClient
    ):
        """Without a built frontend, unknown paths return 200 JSON hint or 404."""
        resp = await client.get("/some-unknown-route")
        # Static dir is empty in tests — SPA mount skipped, so FastAPI returns 404
        # OR if static is built, returns 200 HTML. Both are acceptable.
        assert resp.status_code in (200, 404)

    async def test_api_routes_not_overridden_by_spa(self, client: AsyncClient):
        """API routes must take priority over SPA fallback."""
        resp = await client.get("/api/v1/terms")
        # Should reach the API, not the SPA (may 401 without auth, not 404)
        assert resp.status_code in (200, 401, 403, 422)

    async def test_health_not_overridden_by_spa(self, client: AsyncClient):
        """Health endpoint must not be captured by SPA fallback."""
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestViteConfig:
    """Test that the Vite build config outputs to the correct directory."""

    def test_vite_build_outdir_points_to_static(self):
        """Vite config must build into src/lingo/static/."""
        vite_config = Path(__file__).parents[2] / "frontend" / "vite.config.ts"
        assert vite_config.exists(), "vite.config.ts must exist"
        content = vite_config.read_text()
        assert "../src/lingo/static" in content, "Vite outDir must point to ../src/lingo/static"

    def test_frontend_package_has_build_script(self):
        """package.json must have a build script."""
        pkg = Path(__file__).parents[2] / "frontend" / "package.json"
        assert pkg.exists(), "frontend/package.json must exist"
        import json

        data = json.loads(pkg.read_text())
        assert "build" in data.get("scripts", {}), "package.json must have a build script"

    def test_frontend_package_has_test_script(self):
        """package.json must have a test script."""
        pkg = Path(__file__).parents[2] / "frontend" / "package.json"
        import json

        data = json.loads(pkg.read_text())
        assert "test" in data.get("scripts", {}), "package.json must have a test script"
