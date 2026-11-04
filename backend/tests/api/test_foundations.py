from tests.api.conftest import ApiWorld, seeded


async def test_golden_age_anchorage_and_dedication_views(api: ApiWorld) -> None:
    core = seeded(api).core
    age = await api.http.get(f"/api/worlds/{core.world.id}/golden-age")
    assert age.status_code == 200, age.text
    body = age.json()
    assert body["world_id"] == core.world.id
    assert body["communities"] >= 1
    assert {"prosperity_gain", "decadence", "held", "deepening_epochs"} <= set(body)
    proclaimed = await api.http.post("/api/actions/world:golden_age", json={"world_id": core.world.id})
    assert proclaimed.status_code == 200, proclaimed.text
    held = await api.http.post("/api/actions/foundation:hold", json={"kind": "golden_age", "node_id": core.world.id, "held": True})
    assert held.status_code == 200, held.text
    after = (await api.http.get(f"/api/worlds/{core.world.id}/golden-age")).json()
    assert after["active"] and after["held"]
    anchorage = await api.http.get(f"/api/sons/{core.son.id}/anchorage")
    assert anchorage.status_code == 200, anchorage.text
    assert {"anchor", "anchor_held", "shrines", "creations", "incited"} <= set(anchorage.json())
    assert (await api.http.get("/api/worlds/999999/golden-age")).status_code == 404
    assert (await api.http.get("/api/sons/999999/anchorage")).status_code == 404
    assert (await api.http.get(f"/api/entities/{core.people.id}/dedication")).status_code == 404
