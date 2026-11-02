from tests.api.conftest import ApiWorld, seeded


async def test_personal_notes_list_read_update_delete(api: ApiWorld) -> None:
    people = seeded(api).core.people.id
    assert (await api.http.get("/api/notes")).json() == {"entity_notes": [], "map_notes": []}
    assert (await api.http.get(f"/api/entities/{people}/note")).status_code == 404
    saved = await api.http.put(f"/api/entities/{people}/note", json={"text": "Watch the salt trade."})
    assert saved.status_code == 200, saved.text
    ledger_id = saved.json()["ledger_entry_id"]
    assert ledger_id is not None
    listed = (await api.http.get("/api/notes")).json()
    assert [(note["entity_id"], note["text"]) for note in listed["entity_notes"]] == [(people, "Watch the salt trade.")]
    assert (await api.http.get(f"/api/entities/{people}/note")).json()["text"] == "Watch the salt trade."
    updated = await api.http.put(f"/api/entities/{people}/note", json={"text": "Changed."})
    assert updated.status_code == 200
    deleted = await api.http.delete(f"/api/entities/{people}/note")
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["ledger_entry_id"] is not None
    assert (await api.http.get("/api/notes")).json()["entity_notes"] == []
    undone = await api.http.post(f"/api/ledger/{deleted.json()['ledger_entry_id']}/undo")
    assert undone.status_code == 200, undone.text
    assert (await api.http.get(f"/api/entities/{people}/note")).json()["text"] == "Changed."


async def test_notes_include_map_notes(api: ApiWorld) -> None:
    world = seeded(api).core.world.id
    added = await api.http.post("/api/map-notes", json={"world_id": world, "x": 10, "y": 20, "text": "Camp here"})
    assert added.status_code == 200, added.text
    listed = (await api.http.get("/api/notes")).json()
    assert [note["text"] for note in listed["map_notes"]] == ["Camp here"]
