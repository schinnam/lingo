"""Tests for FastAPI routes using HTTPX async test client."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from lingo.config import settings
from lingo.db.session import get_session
from lingo.main import app
from lingo.models import User
from lingo.models.base import Base

# ---------------------------------------------------------------------------
# Fixtures: in-memory DB wired into the FastAPI app for tests
# ---------------------------------------------------------------------------


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
    """FastAPI test client with DB dependency overridden."""

    async def _override_get_session():
        async with test_session_factory() as sess:
            yield sess

    app.dependency_overrides[get_session] = _override_get_session
    settings.dev_mode = True

    async with test_session_factory() as sess:
        # seed an admin user for auth header
        admin = User(email="admin@lingo.dev", display_name="Admin", role="admin")
        sess.add(admin)
        await sess.commit()
        await sess.refresh(admin)
        admin_id = str(admin.id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac._admin_id = admin_id  # store for test use
        yield ac

    app.dependency_overrides.clear()
    settings.dev_mode = False


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


class TestHealthCheck:
    async def test_health_returns_ok(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


# ---------------------------------------------------------------------------
# Terms CRUD
# ---------------------------------------------------------------------------


class TestCreateTermAPI:
    async def test_create_term(self, client):
        response = await client.post(
            "/api/v1/terms",
            json={
                "name": "BART",
                "definition": "Business Arts Resource Tool",
            },
            headers={"X-User-Id": client._admin_id},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "BART"
        assert data["status"] == "pending"
        assert "id" in data

    async def test_create_term_missing_definition_returns_422(self, client):
        response = await client.post(
            "/api/v1/terms",
            json={"name": "FOO"},
            headers={"X-User-Id": client._admin_id},
        )
        assert response.status_code == 422

    async def test_create_term_without_auth_returns_401(self, client):
        response = await client.post(
            "/api/v1/terms",
            json={"name": "BAR", "definition": "A bar term"},
        )
        assert response.status_code == 401


class TestGetTermAPI:
    async def test_get_existing_term(self, client):
        create = await client.post(
            "/api/v1/terms",
            json={"name": "SRE", "definition": "Site Reliability Engineering"},
            headers={"X-User-Id": client._admin_id},
        )
        term_id = create.json()["id"]

        response = await client.get(f"/api/v1/terms/{term_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "SRE"

    async def test_get_missing_term_returns_404(self, client):
        import uuid

        response = await client.get(f"/api/v1/terms/{uuid.uuid4()}")
        assert response.status_code == 404


class TestListTermsAPI:
    async def test_list_terms(self, client):
        await client.post(
            "/api/v1/terms",
            json={"name": "T1", "definition": "Term one"},
            headers={"X-User-Id": client._admin_id},
        )
        await client.post(
            "/api/v1/terms",
            json={"name": "T2", "definition": "Term two"},
            headers={"X-User-Id": client._admin_id},
        )
        response = await client.get("/api/v1/terms")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 2

    async def test_list_terms_counts_by_status(self, client):
        """counts_by_status reflects all terms, not just the current page."""
        for name in ("S1", "S2"):
            await client.post(
                "/api/v1/terms",
                json={"name": name, "definition": f"Term {name}"},
                headers={"X-User-Id": client._admin_id},
            )
        response = await client.get("/api/v1/terms")
        data = response.json()
        assert "counts_by_status" in data
        # newly created terms are 'pending' by default
        assert data["counts_by_status"].get("pending", 0) >= 2

    async def test_list_terms_filter_by_status(self, client):
        response = await client.get("/api/v1/terms?status=pending")
        assert response.status_code == 200

    async def test_list_terms_search(self, client):
        await client.post(
            "/api/v1/terms",
            json={"name": "DNS", "definition": "Domain Name System"},
            headers={"X-User-Id": client._admin_id},
        )
        response = await client.get("/api/v1/terms?q=Domain")
        assert response.status_code == 200
        names = [t["name"] for t in response.json()["items"]]
        assert "DNS" in names


class TestUpdateTermAPI:
    async def test_update_term(self, client):
        create = await client.post(
            "/api/v1/terms",
            json={"name": "MVP", "definition": "Minimum Viable Product"},
            headers={"X-User-Id": client._admin_id},
        )
        term = create.json()

        response = await client.put(
            f"/api/v1/terms/{term['id']}",
            json={"version": 1, "definition": "Most Valuable Player"},
            headers={"X-User-Id": client._admin_id},
        )
        assert response.status_code == 200
        assert response.json()["definition"] == "Most Valuable Player"
        assert response.json()["version"] == 2

    async def test_update_wrong_version_returns_409(self, client):
        create = await client.post(
            "/api/v1/terms",
            json={"name": "ROI", "definition": "Return on Investment"},
            headers={"X-User-Id": client._admin_id},
        )
        term = create.json()

        response = await client.put(
            f"/api/v1/terms/{term['id']}",
            json={"version": 99, "definition": "Wrong version"},
            headers={"X-User-Id": client._admin_id},
        )
        assert response.status_code == 409


class TestDeleteTermAPI:
    async def test_delete_term(self, client):
        create = await client.post(
            "/api/v1/terms",
            json={"name": "TMP", "definition": "Temporary"},
            headers={"X-User-Id": client._admin_id},
        )
        term_id = create.json()["id"]

        response = await client.delete(
            f"/api/v1/terms/{term_id}",
            headers={"X-User-Id": client._admin_id},
        )
        assert response.status_code == 204

        get = await client.get(f"/api/v1/terms/{term_id}")
        assert get.status_code == 404


class TestExportAPI:
    async def test_export_without_auth_returns_401(self, client):
        response = await client.get("/api/v1/export")
        assert response.status_code == 401

    async def test_export_with_auth_returns_200(self, client):
        response = await client.get(
            "/api/v1/export",
            headers={"X-User-Id": client._admin_id},
        )
        assert response.status_code == 200

    async def test_no_truncated_header_when_within_cap(self, client):
        # Create 3 terms (status=pending by default) — well within the 500-term cap
        for i in range(3):
            await client.post(
                "/api/v1/terms",
                json={"name": f"TermExport{i}", "definition": f"def {i}"},
                headers={"X-User-Id": client._admin_id},
            )
        response = await client.get(
            "/api/v1/export?status=pending",
            headers={"X-User-Id": client._admin_id},
        )
        assert response.status_code == 200
        assert "lingo-truncated" not in response.headers

    async def test_truncated_header_when_cap_exceeded(self, client):
        # Create 4 terms but request only 2 — simulates hitting the cap
        for i in range(4):
            await client.post(
                "/api/v1/terms",
                json={"name": f"TermCap{i}", "definition": f"def {i}"},
                headers={"X-User-Id": client._admin_id},
            )
        response = await client.get(
            "/api/v1/export?status=pending&limit=2",
            headers={"X-User-Id": client._admin_id},
        )
        assert response.status_code == 200
        assert response.headers.get("lingo-truncated") == "true"

    async def test_offset_pagination_returns_remaining_terms(self, client):
        for i in range(3):
            await client.post(
                "/api/v1/terms",
                json={"name": f"TermPage{i}", "definition": f"def {i}"},
                headers={"X-User-Id": client._admin_id},
            )
        # First page: limit=2
        first = await client.get(
            "/api/v1/export?status=pending&limit=2",
            headers={"X-User-Id": client._admin_id},
        )
        # Second page: offset=2
        second = await client.get(
            "/api/v1/export?status=pending&limit=2&offset=2",
            headers={"X-User-Id": client._admin_id},
        )
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.headers.get("lingo-truncated") == "true"
        assert "lingo-truncated" not in second.headers


class TestVoteAPI:
    async def test_vote_on_term(self, client):
        create = await client.post(
            "/api/v1/terms",
            json={"name": "CI", "definition": "Continuous Integration"},
            headers={"X-User-Id": client._admin_id},
        )
        term_id = create.json()["id"]

        response = await client.post(
            f"/api/v1/terms/{term_id}/vote",
            headers={"X-User-Id": client._admin_id},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["vote_count"] >= 1

    async def test_duplicate_vote_returns_409(self, client):
        create = await client.post(
            "/api/v1/terms",
            json={"name": "CD", "definition": "Continuous Deployment"},
            headers={"X-User-Id": client._admin_id},
        )
        term_id = create.json()["id"]

        await client.post(
            f"/api/v1/terms/{term_id}/vote",
            headers={"X-User-Id": client._admin_id},
        )
        response = await client.post(
            f"/api/v1/terms/{term_id}/vote",
            headers={"X-User-Id": client._admin_id},
        )
        assert response.status_code == 409
