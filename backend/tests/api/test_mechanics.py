from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import MortalStats
from aerona.engine.interconnect.explorer import affects_by_writer
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
    reach = affects_by_writer()
    for acting in view["acting"]:
        assert set(acting["affects"]) <= {str(target) for target in reach.get(acting["key"], frozenset())}
    assert any(acting["affects"] for acting in view["acting"])


async def test_a_place_without_stats_still_opens_its_mechanics(api: ApiWorld) -> None:
    region = seeded(api).core.regions[0]
    response = await api.http.get(f"/api/nodes/{region.id}/mechanics")
    assert response.status_code == 200, response.text
    assert response.json()["node_id"] == region.id


async def test_the_registry_graph_and_a_mechanic_s_links_are_served(api: ApiWorld) -> None:
    graph = await api.http.get("/api/mechanics/graph")
    assert graph.status_code == 200, graph.text
    body = graph.json()
    assert {item["key"] for item in body["subsystems"]} >= {"core", "body", "environment"}
    assert any("modifier" in link["kinds"] for link in body["links"])
    links = await api.http.get("/api/mechanics/modifiers/links")
    assert links.status_code == 200, links.text
    assert links.json()["mechanic"]["key"] == "modifiers"
    assert (await api.http.get("/api/mechanics/nowhere/links")).status_code == 404


async def test_a_written_incident_shows_in_the_causality_graph(api: ApiWorld) -> None:
    region = seeded(api).core.regions[0]
    place = [{"node_id": region.id, "role": "place"}]
    opening = {"text": "The river rose.", "kind": "player.history", "magnitude": 30, "participants": place}
    first = await api.http.post("/api/actions/incident:create", json=opening)
    assert first.status_code == 200, first.text
    root = first.json()["created_ids"][0]
    struck = [{"node_id": region.id, "role": "target"}]
    body = {"text": "The fields drowned.", "kind": "player.history", "magnitude": 30, "cause_incident_id": root, "participants": struck}
    second = await api.http.post("/api/actions/incident:create", json=body)
    assert second.status_code == 200, second.text
    response = await api.http.get(f"/api/nodes/{region.id}/causality")
    assert response.status_code == 200, response.text
    assert {"cause": root, "effect": second.json()["created_ids"][0], "span": 0} in response.json()["edges"]
