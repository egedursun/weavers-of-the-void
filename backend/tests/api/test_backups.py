from tests.api.conftest import ApiWorld


async def test_backups_take_list_download_and_guard_restore(api: ApiWorld) -> None:
    taken = await api.http.post("/api/backups")
    assert taken.status_code == 200, taken.text
    name = taken.json()["file"]
    assert name in [item["file"] for item in (await api.http.get("/api/backups")).json()]
    download = await api.http.get(f"/api/backups/{name}/database")
    assert download.status_code == 200
    assert download.content.startswith(b"SQLite format 3")
    assert (await api.http.get("/api/backups/missing.db/database")).status_code == 404
    package = await api.http.get(f"/api/backups/{name}/package")
    assert package.status_code == 200
    assert package.content[:2] == b"\x1f\x8b"
    wrong = await api.http.post("/api/backups/restore", json={"file": name, "confirm": "restore"})
    assert wrong.status_code == 400
    restored = await api.http.post("/api/backups/restore", json={"file": name, "confirm": "RESTORE"})
    assert restored.status_code == 200, restored.text
    assert restored.json()["safety_backup"]


async def test_reset_needs_the_typed_word(api: ApiWorld) -> None:
    assert (await api.http.post("/api/world/reset", json={"confirm": "reset"})).status_code == 400
    reset = await api.http.post("/api/world/reset", json={"confirm": "RESET"})
    assert reset.status_code == 200, reset.text
    assert (await api.http.get("/api/state")).json()["world"] is None
