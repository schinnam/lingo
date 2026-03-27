"""Integration tests for /api/v1/terms — hits a real Postgres database."""
import pytest


class TestCreateTerm:
    async def test_create_term_returns_201(self, client, test_user):
        response = await client.post(
            "/api/v1/terms",
            json={"name": "API", "definition": "Application Programming Interface"},
            headers={"X-User-Id": str(test_user.id)},
        )
        assert response.status_code == 201

    async def test_create_term_returns_correct_fields(self, client, test_user):
        response = await client.post(
            "/api/v1/terms",
            json={
                "name": "ETL",
                "definition": "Extract, Transform, Load",
                "full_name": "Extract Transform Load",
                "category": "data",
            },
            headers={"X-User-Id": str(test_user.id)},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "ETL"
        assert data["definition"] == "Extract, Transform, Load"
        assert data["full_name"] == "Extract Transform Load"
        assert data["category"] == "data"
        assert data["status"] == "pending"
        assert "id" in data

    async def test_create_term_requires_auth(self, client):
        response = await client.post(
            "/api/v1/terms",
            json={"name": "SLA", "definition": "Service Level Agreement"},
        )
        assert response.status_code == 401


class TestListTerms:
    async def test_list_terms_returns_200(self, client):
        response = await client.get("/api/v1/terms")
        assert response.status_code == 200

    async def test_list_terms_includes_created_term(self, client, test_user):
        await client.post(
            "/api/v1/terms",
            json={"name": "SLO", "definition": "Service Level Objective"},
            headers={"X-User-Id": str(test_user.id)},
        )
        response = await client.get("/api/v1/terms")
        assert response.status_code == 200
        data = response.json()
        names = [t["name"] for t in data["items"]]
        assert "SLO" in names

    async def test_list_terms_response_shape(self, client):
        response = await client.get("/api/v1/terms")
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "offset" in data
        assert "limit" in data
