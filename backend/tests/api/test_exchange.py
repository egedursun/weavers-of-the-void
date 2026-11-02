from tests.api.conftest import ApiWorld


async def test_export_then_open_as_discovery_is_read_only(api: ApiWorld) -> None:
    exported = await api.http.get("/api/world/export", params={"images": False})
    assert exported.status_code == 200
    assert "attachment" in exported.headers["content-disposition"]
    package = exported.content
    refused = await api.http.post(
        "/api/world/import", params={"mode": "replace", "confirm": "replace"}, content=package, headers={"content-type": "application/octet-stream"}
    )
    assert refused.status_code == 400
    opened = await api.http.post("/api/world/import", params={"mode": "discovery"}, content=package, headers={"content-type": "application/octet-stream"})
    assert opened.status_code == 200, opened.text
    assert (await api.http.get("/api/discovery")).json()["active"] is True
    state = (await api.http.get("/api/state")).json()
    assert state["read_only"] is True
    assert state["world"] is not None
    locked = await api.http.patch("/api/creator", json={"title": "Intruder"})
    assert locked.status_code == 423
    assert locked.json()["code"] == "read_only"
    ended = await api.http.post("/api/discovery/end")
    assert ended.status_code == 200, ended.text
    assert (await api.http.get("/api/discovery")).json()["active"] is False


async def test_import_refuses_garbage(api: ApiWorld) -> None:
    response = await api.http.post("/api/world/import", content=b"garbage", headers={"content-type": "application/octet-stream"})
    assert response.status_code == 400


async def test_merge_requires_typed_confirmation_and_reports_summary(api: ApiWorld) -> None:
    package = (await api.http.get("/api/world/export", params={"images": False})).content
    headers = {"content-type": "application/octet-stream"}
    refused = await api.http.post("/api/world/import", params={"mode": "merge", "confirm": "merge"}, content=package, headers=headers)
    assert refused.status_code == 400
    merged = await api.http.post("/api/world/import", params={"mode": "merge", "confirm": "MERGE"}, content=package, headers=headers)
    assert merged.status_code == 200, merged.text
    body = merged.json()
    assert body["mode"] == "merge"
    assert body["safety_backup"]
    assert body["merge"]["rows"]["nodes"] > 0
    assert body["merge"]["renamed"]
