from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityType
from aerona.engine.phases.environment import environment_survey
from aerona.engine.primitives.manual import manual_context
from tests.api.conftest import ApiWorld, seeded


async def town_and_region(api: ApiWorld) -> tuple[int, int]:
    async with api.services.database.read() as session:
        town = await session.scalar(select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.name == "Harrowmere"))
    assert town is not None and town.location_id is not None
    return town.id, town.location_id


async def test_the_city_scene_draws_the_engines_districts_buildings_and_homes(api: ApiWorld) -> None:
    town_id, _ = await town_and_region(api)
    built = await api.http.post("/api/actions/district:build", json={"settlement_id": town_id, "kind": "residential", "material": "timber"})
    assert built.status_code == 200, built.text
    begun = await api.http.post("/api/actions/structure:commission", json={"site_id": town_id, "kind": "school", "level": 1, "funds": 0})
    assert begun.status_code == 200, begun.text
    scene = (await api.http.get(f"/api/city/{town_id}")).json()
    residential = [row for row in scene["districts"] if row["kind"] == "residential"]
    assert residential and residential[0]["zone"] == "residential" and residential[0]["cells"]
    seeds = [(row["q"], row["r"]) for row in scene["districts"]]
    assert len(seeds) == len(set(seeds))
    school = next(row for row in scene["buildings"] if row["kind"] == "school")
    assert school["zone"] == "civic" and school["civic"] == "education" and school["state"] in ("planned", "building")
    assert scene["scale"] >= 1 and {row["zone"] for row in scene["zones"]} >= {"residential", "civic", "green"}
    assert (await api.http.get("/api/city/999999")).status_code == 404


async def test_the_god_moves_a_district_sets_its_homes_and_releases_it(api: ApiWorld) -> None:
    town_id, _ = await town_and_region(api)
    await api.http.post("/api/actions/district:build", json={"settlement_id": town_id, "kind": "gardens", "material": "timber"})
    scene = (await api.http.get(f"/api/city/{town_id}")).json()
    district = next(row for row in scene["districts"] if row["kind"] == "gardens")
    moved = await api.http.post("/api/actions/district:move", json={"district_id": district["id"], "q": 11, "r": -5})
    assert moved.status_code == 200, moved.text
    moved_scene = (await api.http.get(f"/api/city/{town_id}")).json()
    other = next(row for row in moved_scene["districts"] if row["id"] != district["id"])
    clash = await api.http.post("/api/actions/district:move", json={"district_id": district["id"], "q": other["q"], "r": other["r"]})
    assert clash.status_code == 409, clash.text
    homes = await api.http.post("/api/actions/district_urban:edit", json={"district_id": district["id"], "values": {"housing": "manor"}, "release": []})
    assert homes.status_code == 200, homes.text
    after = next(row for row in (await api.http.get(f"/api/city/{town_id}")).json()["districts"] if row["id"] == district["id"])
    assert (after["q"], after["r"]) == (11, -5) and after["housing"] == "manor" and {"hex", "housing"} <= set(after["locked"])
    released = await api.http.post("/api/actions/district_urban:edit", json={"district_id": district["id"], "values": {}, "release": after["locked"]})
    assert released.status_code == 200, released.text
    final = next(row for row in (await api.http.get(f"/api/city/{town_id}")).json()["districts"] if row["id"] == district["id"])
    assert final["locked"] == []


async def test_the_land_scene_follows_the_land_and_types_gather_their_buildings(api: ApiWorld) -> None:
    town_id, region_id = await town_and_region(api)
    async with api.services.database.write() as session:
        await environment_survey(await manual_context(session, "environment", rules=api.services.rules.current))
    shaped = await api.http.post("/api/actions/environment:set", json={"region_id": region_id, "field": "forest_cover", "value": 100, "lock": True})
    assert shaped.status_code == 200, shaped.text
    land = (await api.http.get(f"/api/land/{region_id}")).json()
    dry = [tile for tile in land["tiles"] if tile["ground"] not in ("water", "shore")]
    assert land["forest_cover"] == 100 and dry
    assert sum(1 for tile in dry if tile["cover"] == "forest") >= len(dry) // 2
    assert town_id in {row["node"]["id"] for row in land["settlements"]}
    assert (await api.http.get(f"/api/land/{town_id}")).status_code == 404
    await api.http.post("/api/actions/structure:commission", json={"site_id": town_id, "kind": "school", "level": 1, "funds": 0})
    world_id = seeded(api).core.world.id
    types = (await api.http.get(f"/api/structure-types/{world_id}")).json()
    school = next(row for row in types["structures"] if row["kind"] == "school")
    assert school["zone"] == "civic" and school["instances"]
    assert {row["housing"] for row in types["dwellings"]} == {"hut", "cottage", "house", "townhouse", "manor"}


async def test_the_book_and_the_codex_draw_the_city_plan_and_gather_building_types(api: ApiWorld) -> None:
    town_id, _ = await town_and_region(api)
    await api.http.post("/api/actions/district:build", json={"settlement_id": town_id, "kind": "civic_quarter", "material": "stone"})
    await api.http.post("/api/actions/structure:commission", json={"site_id": town_id, "kind": "almshouse", "level": 1, "funds": 0})
    book = (await api.http.get("/api/book")).text
    assert 'aria-label="Plan of Harrowmere"' in book and "its districts by zone on their hexes" in book
    assert "Building types" in book and "Almshouse" in book and "Home types" in book
    codex = (await api.http.get("/api/codex.md")).text
    assert "| Part of the plan | What stands there |" in codex and "Civic zone" in codex
    assert "Building types" in codex and "Almshouse" in codex
