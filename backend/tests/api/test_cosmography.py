from tests.api.conftest import ApiWorld, seeded


async def test_the_heavens_are_read_shaped_and_held(api: ApiWorld) -> None:
    world = seeded(api).core.world
    catalog = (await api.http.get("/api/cosmography/catalog")).json()
    assert {"galaxy_types", "dimension_kinds", "being_kinds", "phenomenon_kinds", "method_reach"} <= set(catalog)
    made = await api.http.post("/api/actions/dimension:create", json={"name": "Astral Reach", "kind": "astral"})
    assert made.status_code == 200, made.text
    view = (await api.http.get("/api/cosmography")).json()
    plane = next(row for row in view["dimensions"] if row["name"] == "Astral Reach")
    galaxy = await api.http.post("/api/actions/galaxy:create", json={"name": "Far Wheel", "galaxy_type": "spiral", "dimension_id": plane["id"]})
    assert galaxy.status_code == 200, galaxy.text
    edited = await api.http.post("/api/actions/dimension:edit", json={"dimension_id": plane["id"], "values": {"veil": 12}})
    assert edited.status_code == 200, edited.text
    view = (await api.http.get("/api/cosmography")).json()
    plane = next(row for row in view["dimensions"] if row["id"] == plane["id"])
    assert plane["veil"] == 12 and "veil" in plane["locked"]
    assert any(row["name"] == "Far Wheel" and row["dimension_id"] == plane["id"] for row in view["galaxies"])
    assert str(world.id) in view["world_names"]
    placement = next(row for row in view["placements"] if row["world_id"] == world.id)
    assert placement["pull"]["time"] > 0
    assert (await api.http.post("/api/actions/dimension:edit", json={"dimension_id": 999999, "values": {"veil": 1}})).status_code == 404
