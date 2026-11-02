from tests.api.conftest import ApiWorld


async def test_notes_list_read_and_settings(api: ApiWorld) -> None:
    created = await api.http.post("/api/notifications", json={"title": "Remember the salt road", "body": "Before the floods."})
    assert created.status_code == 200, created.text
    listing = (await api.http.get("/api/notifications", params={"category": "note"})).json()
    assert listing["items"][0]["title"] == "Remember the salt road"
    assert listing["unread"] >= 1
    marked = await api.http.post("/api/notifications/read", json={"every": True})
    assert marked.json()["changed"] >= 1
    assert (await api.http.get("/api/notifications", params={"unread_only": True})).json()["items"] == []
    settings = await api.http.put("/api/notifications/settings", json={"war": False})
    assert settings.json()["war"] is False
    assert (await api.http.post("/api/notifications", json={"title": ""})).status_code == 400
