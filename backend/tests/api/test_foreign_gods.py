from aerona.db.repositories.foreign_gods import ForeignGodDraft, ForeignGodRepository
from aerona.domain.enums.domain import Domain
from aerona.domain.models.stats import StatBlock
from tests.api.conftest import ApiWorld, seeded


async def test_foreign_god_detail_and_edit(api: ApiWorld) -> None:
    world = seeded(api).core
    async with api.services.database.write() as session:
        god = await ForeignGodRepository(session).create(
            ForeignGodDraft(
                name="Ushmar",
                world_id=world.world.id,
                domain_primary=Domain.DEATH,
                power=40,
                stats=StatBlock(strength=50, endurance=50, agility=50, wisdom=50, cunning=50, will=50, creativity=50, charisma=50, might=50),
                created_epoch=1,
            )
        )
        god_id = god.id
    listing = (await api.http.get("/api/foreign-gods")).json()
    assert [item["id"] for item in listing] == [god_id]
    detail = (await api.http.get(f"/api/foreign-gods/{god_id}")).json()
    assert detail["god"]["name"] == "Ushmar"
    edited = await api.http.patch(f"/api/foreign-gods/{god_id}", json={"stance": 20})
    assert edited.status_code == 200, edited.text
    assert (await api.http.get("/api/foreign-gods/999999")).status_code == 404
    assert (await api.http.post(f"/api/foreign-gods/{god_id}/deepen")).status_code in (400, 409)


async def test_placing_an_old_god_accepts_an_image_prompt(api: ApiWorld) -> None:
    world = seeded(api).core
    schema = (await api.http.get("/openapi.json")).json()["components"]["schemas"]["PostForeignGodsBody"]
    assert "image_prompt" in schema["properties"]
    response = await api.http.post("/api/foreign-gods", json={"world_id": world.world.id, "name": "Ember Mother", "image_prompt": "a mother of embers"})
    assert response.status_code in (200, 202), response.text
    god_id = response.json()["target_node_id"]
    detail = (await api.http.get(f"/api/foreign-gods/{god_id}")).json()
    assert detail["god"]["image_prompt"] == "a mother of embers"
