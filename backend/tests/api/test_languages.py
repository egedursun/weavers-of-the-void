from tests.api.conftest import ApiWorld, seeded


async def test_languages_tree_and_knowledge(api: ApiWorld) -> None:
    world = seeded(api).core
    languages = (await api.http.get("/api/languages")).json()
    assert world.language.id in [item["language"]["id"] for item in languages]
    tree = (await api.http.get("/api/languages/tree")).json()
    assert world.language.id in [item["language"]["id"] for item in tree]
    own = next(item for item in tree if item["language"]["id"] == world.language.id)
    assert isinstance(own["sample_names"], list) and isinstance(own["cognates"], list)
    knowledge = (await api.http.get("/api/knowledge")).json()
    assert len(knowledge) == 4
    assert all(item["knowers"] for item in knowledge)
    assert all(isinstance(item["prerequisites"], list) for item in knowledge)


async def test_translation_needs_the_language_model(api: ApiWorld) -> None:
    language = seeded(api).core.language.id
    assert (await api.http.post(f"/api/languages/{language}/translate", json={"text": "Salt and stone."})).status_code == 409
    assert (await api.http.post(f"/api/languages/{language}/translate", json={"text": ""})).status_code == 400
