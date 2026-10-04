import pytest
from httpx import ASGITransport, AsyncClient
from app.main import create_app
from app.config import Settings


@pytest.fixture
def app():
    settings = Settings(
        secret_key="test-secret",
        shelter_backend_api_key="test-dev-secret",
        redis_url="redis://localhost:6379",
        agent_service_url="http://localhost:8000",
    )
    return create_app(settings)


@pytest.mark.asyncio
async def test_search_children(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/children/search",
            json={
                "criteria": {
                    "gender": "male",
                    "age": {"exact": 7},
                    "last_seen_location": "Saddar",
                },
                "max_results": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "candidates" in data
        assert len(data["candidates"]) > 0
        top = data["candidates"][0]
        assert top["case_id"] == "WF-CASE-2026-00412"
        assert top["metadata_match_score"] > 0.5


@pytest.mark.asyncio
async def test_submit_found_child(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/children/found",
            json={
                "estimated_age": 6,
                "gender": "female",
                "found_location": "Liberty Market",
                "clothing": "Red shirt",
                "finder_contact": "+92 300 1234567",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["case_reference"].startswith("WF-FOUND-")
        assert len(data["next_steps"]) > 0


@pytest.mark.asyncio
async def test_get_case_status(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/cases/WF-CASE-2026-00412")
        assert response.status_code == 200
        data = response.json()
        assert data["case_reference"] == "WF-CASE-2026-00412"
        assert data["status"] == "under_review"


@pytest.mark.asyncio
async def test_guardian_register_and_list_children(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register a child
        reg_response = await client.post(
            "/api/guardians/register-child",
            json={
                "guardian_name": "Farhan Ali",
                "guardian_phone": "+92 321 9876543",
                "child_name": "Bilal Ali",
                "age": 8,
                "gender": "male",
                "hair_color": "black",
            },
        )
        assert reg_response.status_code == 200
        reg_data = reg_response.json()
        assert reg_data["success"] is True
        assert reg_data["child_name"] == "Bilal Ali"
        assert reg_data["status"] == "REGISTERED_SAFE"

        # List registered children
        guardian_id = reg_data["guardian_id"]
        list_response = await client.get(f"/api/guardians/{guardian_id}/children")
        assert list_response.status_code == 200
        list_data = list_response.json()
        assert len(list_data) == 1
        assert list_data[0]["name"] == "Bilal Ali"
