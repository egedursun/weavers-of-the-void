from tests.api.conftest import ApiWorld, seeded


async def test_map_is_generated_and_notes_round_trip(api: ApiWorld) -> None:
    world = seeded(api).core.world
    view = (await api.http.get(f"/api/worlds/{world.id}/map")).json()
    assert view["geometry"]["regions"]
    assert view["time"]["current"] == view["time"]["shown"]
    assert {"roads", "relations", "wars", "region_creators"} <= set(view)
    assert all(len(road["path"]) >= 4 for road in view["roads"])
    regions = {point["entity"]["id"] for point in view["points"] if point["entity"]["entity_type"] == "region"}
    assert {int(key) for key in view["region_creators"]} == regions
    added = await api.http.post("/api/map-notes", json={"world_id": world.id, "x": 10, "y": 20, "text": "Here be salt."})
    assert added.status_code == 200, added.text
    notes = (await api.http.get("/api/map-notes", params={"world_id": world.id})).json()
    assert [note["text"] for note in notes] == ["Here be salt."]
    removed = await api.http.delete(f"/api/map-notes/{notes[0]['id']}")
    assert removed.status_code == 200
    assert (await api.http.get("/api/worlds/999999/map")).status_code == 404
    assert (await api.http.get(f"/api/worlds/{world.id}/map", params={"epoch": 0})).status_code == 400
