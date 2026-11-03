from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import MortalStats
from aerona.engine.interconnect.edges import GENERIC_CARRIERS, all_edges
from tests.api.conftest import ApiWorld, seeded
from tests.engine.core.factories import entity


async def test_a_fresh_mortal_shows_why_each_value_is_what_it_is(api: ApiWorld) -> None:
    core = seeded(api).core
    async with api.services.database.write() as session:
        mortal = await entity(session, "Narir", EntityType.MORTAL, MortalStats(hp=80), world_id=core.world.id, location_id=core.regions[0].id)
        mortal_id = mortal.id
    added = await api.http.post("/api/actions/modifier:add", json={"node_id": mortal_id, "key": "hp", "op": "add", "magnitude": 5})
    assert added.status_code == 200, added.text
    response = await api.http.get(f"/api/nodes/{mortal_id}/mechanics")
    assert response.status_code == 200, response.text
    view = response.json()
    hp = next(item for item in view["effective"] if item["key"] == "hp")
    assert (hp["base"], hp["value"]) == (80, 85)
    assert [item["key"] for item in view["modifiers"]] == ["hp"]
    assert view["acting"]
    for acting in view["acting"]:
        reached = {str(edge.target) for edge in all_edges() if edge.writer == acting["key"] and edge.carrier not in GENERIC_CARRIERS}
        assert set(acting["affects"]) <= reached
    assert any(acting["affects"] for acting in view["acting"])


async def test_a_place_without_stats_still_opens_its_mechanics(api: ApiWorld) -> None:
    region = seeded(api).core.regions[0]
    response = await api.http.get(f"/api/nodes/{region.id}/mechanics")
    assert response.status_code == 200, response.text
    assert response.json()["node_id"] == region.id
