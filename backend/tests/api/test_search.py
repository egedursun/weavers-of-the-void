from tests.api.conftest import ApiWorld, seeded


async def test_names_cover_sons_and_entities(api: ApiWorld) -> None:
    world = seeded(api).core
    names = {(item["kind"], item["id"]) for item in (await api.http.get("/api/names")).json()}
    assert ("son", world.son.id) in names
    assert ("entity", world.people.id) in names


async def test_search_needs_two_characters_and_finds_records(api: ApiWorld) -> None:
    assert (await api.http.get("/api/search", params={"q": "H"})).json() == []
    hits = (await api.http.get("/api/search", params={"q": "Harrowmere"})).json()
    assert any(hit["title"] == "Harrowmere" for hit in hits)
    too_long = await api.http.get("/api/search", params={"q": "x" * 300})
    assert too_long.status_code == 400
    assert too_long.json()["code"] == "invalid"
