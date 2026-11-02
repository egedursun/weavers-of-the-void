from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.society import AddictionRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.phonology import Phonology
from tests.api.conftest import ApiWorld, seeded
from tests.services.player.factories import make_entity, seed_player_world


async def test_cosmos_overview_and_guide(api: ApiWorld) -> None:
    world = seeded(api).core.world
    cosmos = (await api.http.get("/api/cosmos")).json()
    assert [item["world"]["id"] for item in cosmos["worlds"]] == [world.id]
    assert cosmos["world_types"]
    summary = (await api.http.get("/api/discovery-summary")).json()
    assert summary["worlds"][0]["world_id"] == world.id
    guide = (await api.http.get(f"/api/worlds/{world.id}/guide")).json()
    assert guide["world"]["name"] == world.name
    assert (await api.http.get("/api/worlds/999999/guide")).status_code == 404


async def test_world_edits_go_through_actions(api: ApiWorld) -> None:
    world = seeded(api).core.world
    edited = await api.http.patch(f"/api/worlds/{world.id}", json={"description": "A salt-white world."})
    assert edited.status_code == 200, edited.text
    assert (await api.http.patch("/api/stars/999999", json={"name": "Nowhere"})).status_code == 404
    climate = await api.http.put("/api/climate", json={"era": "ice_age", "epochs": 2, "world_id": world.id})
    assert climate.status_code == 200, climate.text
    bad = await api.http.post("/api/cosmic/sky-event", json={"kind": "not_an_event"})
    assert bad.status_code == 400


async def test_addictions_are_listed_and_cured(empty_api: ApiWorld) -> None:
    async with empty_api.services.database.write() as session:
        world = await seed_player_world(session)
        town = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
        salt = await make_entity(session, "Dream Salt", EntityType.RESOURCE, world_id=world.world.id, location_id=world.region.id)
        session.add(AddictionRow(community_entity_id=town.id, resource_entity_id=salt.id, owned_epochs=4, addicted_since_epoch=1))
    listing = (await empty_api.http.get("/api/addictions", params={"community_id": town.id})).json()
    assert [(item["community"]["name"], item["resource"]["name"], item["owned_epochs"]) for item in listing] == [("Ashford", "Dream Salt", 4)]
    cured = await empty_api.http.post("/api/actions/addiction:cure", json={"entity_id": town.id, "resource_id": salt.id})
    assert cured.status_code == 200, cured.text
    assert (await empty_api.http.get("/api/addictions")).json() == []


async def test_world_records_carry_their_dialect(api: ApiWorld) -> None:
    world_id = seeded(api).core.world.id
    dialect = Phonology(
        vowels=("a", "o"),
        consonants=("k", "r"),
        forbidden_sounds=("z",),
        syllable_patterns=("CV", "CVC"),
        preferred_endings=("ar",),
        min_syllables=2,
        max_syllables=3,
        sample_names=("Korar",),
    )
    async with api.services.database.write() as session:
        row = await session.get(WorldRow, world_id)
        assert row is not None
        row.phonology = dialect
    guide = (await api.http.get(f"/api/worlds/{world_id}/guide")).json()
    assert guide["world"]["phonology"]["sample_names"] == ["Korar"]
    assert guide["world"]["phonology"]["forbidden_sounds"] == ["z"]
    cosmos = (await api.http.get("/api/cosmos")).json()
    assert cosmos["worlds"][0]["world"]["phonology"]["preferred_endings"] == ["ar"]
