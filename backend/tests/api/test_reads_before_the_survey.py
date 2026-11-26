from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import SettlementStats, SpeciesStats, StructureStats
from tests.api.conftest import ApiWorld, seeded
from tests.engine.core.factories import entity

MISSING = 987_654


async def test_a_thing_founded_this_epoch_answers_null_until_it_is_surveyed(api: ApiWorld) -> None:
    core = seeded(api).core
    region = core.regions[0]
    async with api.services.database.write() as session:
        town = await entity(session, "Nici", EntityType.SETTLEMENT, SettlementStats(population=300), world_id=core.world.id, location_id=region.id)
        kind = await entity(session, "Marsh Hare", EntityType.SPECIES, SpeciesStats(), world_id=core.world.id)
        work = await entity(session, "New Bridge", EntityType.STRUCTURE, StructureStats(), world_id=core.world.id, location_id=town.id)
        ids = (town.id, kind.id, work.id)
    town_id, kind_id, work_id = ids
    for path in (
        f"/api/minds/{town_id}",
        f"/api/entities/{town_id}/settlement-plan",
        f"/api/entities/{kind_id}/ecology",
        f"/api/entities/{work_id}/structure",
        f"/api/presence/speakers/{town_id}",
    ):
        answer = await api.http.get(path)
        assert (answer.status_code, answer.json()) == (200, None), path


async def test_a_thing_that_does_not_exist_still_answers_not_found(api: ApiWorld) -> None:
    for path in (
        f"/api/minds/{MISSING}",
        f"/api/places/{MISSING}/profile",
        f"/api/regions/{MISSING}/terrain",
        f"/api/regions/{MISSING}/environment",
        f"/api/entities/{MISSING}/ecology",
        f"/api/entities/{MISSING}/structure",
        f"/api/presence/speakers/{MISSING}",
    ):
        assert (await api.http.get(path)).status_code == 404, path
