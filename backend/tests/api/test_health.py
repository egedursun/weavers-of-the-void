from httpx import AsyncClient


async def test_health_reports_database_ok(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["database_ok"] is True
    assert body["llm_enabled"] is False
    assert body["running_jobs"] == 0
