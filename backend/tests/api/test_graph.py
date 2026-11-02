from tests.api.conftest import ApiWorld, seeded


async def test_graph_window_and_health(api: ApiWorld) -> None:
    window = (await api.http.get("/api/graph", params={"node_limit": 3, "link_limit": 2})).json()
    assert len(window["nodes"]) == 3
    assert window["node_total"] >= 3
    assert len(window["links"]) <= 2
    health = (await api.http.get("/api/graph/health")).json()
    assert health["nodes"] > 0
    repaired = await api.http.post("/api/graph/repair")
    assert repaired.status_code == 200
    assert "total" in repaired.json()["counters"]


async def test_path_finder_spans_node_kinds(api: ApiWorld) -> None:
    world = seeded(api).core
    found = (await api.http.get("/api/graph/path", params={"a": world.son.id, "b": world.extra["town"].id})).json()
    assert found["found"] is True
    assert found["path"][0] == world.son.id
    creator = (await api.http.get("/api/graph/path", params={"a": world.creator.id, "b": world.world.id})).json()
    assert creator["path"] == [] or creator["path"][0] == world.creator.id
    missing = (await api.http.get("/api/graph/path", params={"a": world.son.id, "b": 999999})).json()
    assert missing["found"] is False
    assert (await api.http.get("/api/graph/path", params={"a": "x", "b": 1})).status_code == 400


async def test_fate_link_needs_the_language_model(api: ApiWorld) -> None:
    assert (await api.http.post("/api/graph/fate-link", json={})).status_code == 409
    assert (await api.http.post("/api/graph/fate-link/stop")).json()["ok"] is False


async def test_graph_nodes_carry_their_world(api: ApiWorld) -> None:
    world = seeded(api).core.world
    window = (await api.http.get("/api/graph")).json()
    entities = [node for node in window["nodes"] if node["kind"] == "entity"]
    assert entities and all(node["world_id"] == world.id for node in entities)
