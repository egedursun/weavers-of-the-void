from tests.api.conftest import ApiWorld


async def test_world_settings_read_and_update(api: ApiWorld) -> None:
    current = (await api.http.get("/api/settings")).json()
    assert current["llm_enabled"] is False
    updated = await api.http.patch("/api/settings", json={"fate_mode": "off"})
    assert updated.status_code == 200, updated.text
    assert (await api.http.get("/api/settings")).json()["fate_mode"] == "off"
    assert (await api.http.patch("/api/settings", json={"fate_mode": "sometimes"})).status_code == 400


async def test_settings_need_a_world(empty_api: ApiWorld) -> None:
    assert (await empty_api.http.get("/api/settings")).status_code in (400, 404, 409)
