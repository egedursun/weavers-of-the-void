from tests.api.conftest import ApiWorld, seeded


async def test_player_routes_cheat_federate_and_awaken(api: ApiWorld) -> None:
    world = seeded(api).core
    cheat = await api.http.post("/api/cheats/essence", json={"amount": 50})
    assert cheat.status_code == 200, cheat.text
    assert cheat.json()["essence_gained"] == 50
    assert (await api.http.post("/api/cheats/essence", json={"amount": 0})).status_code == 400
    federation = await api.http.post("/api/federations", json={"member_ids": [world.extra["town"].id], "name": "Salt League"})
    assert federation.status_code == 400
    assert (await api.http.post("/api/peoples/awaken", json={"count": 1})).status_code in (400, 409)
