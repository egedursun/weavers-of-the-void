from tests.api.conftest import ApiWorld, seeded


async def test_world_and_star_wiki_pages(api: ApiWorld) -> None:
    world = seeded(api).core.world
    wiki = (await api.http.get(f"/api/worlds/{world.id}/wiki")).json()
    assert wiki["world"]["name"] == world.name
    assert wiki["type_label"]
    assert wiki["counts"]["peoples"] >= 1
    assert wiki["peoples"]
    assert world.star_id is not None
    star = (await api.http.get(f"/api/stars/{world.star_id}/wiki")).json()
    assert [item["world"]["id"] for item in star["worlds"]] == [world.id]
    assert (await api.http.get("/api/worlds/999999/wiki")).status_code == 404
    assert (await api.http.get("/api/stars/999999/wiki")).status_code == 404


async def test_world_and_star_lore_is_rewritten_by_hand(api: ApiWorld) -> None:
    world = seeded(api).core.world
    edited = await api.http.post(
        "/api/actions/world:depth",
        json={
            "world_id": world.id,
            "history": "The sea came first.",
            "rumours": ["The tide speaks.", "  "],
            "sayings": [{"form": "proverb", "text": "Salt remembers."}],
        },
    )
    assert edited.status_code == 200, edited.text
    depth = (await api.http.get(f"/api/worlds/{world.id}/wiki")).json()["depth"]
    assert depth["history"] == "The sea came first."
    assert depth["rumours"] == ["The tide speaks."]
    assert depth["sayings"] == [{"form": "proverb", "text": "Salt remembers."}]
    star = await api.http.post("/api/actions/star:depth", json={"star_id": world.star_id, "hidden_truth": "It is a sleeping god."})
    assert star.status_code == 200, star.text
    assert (await api.http.post("/api/actions/star:depth", json={"star_id": world.star_id})).status_code == 400
