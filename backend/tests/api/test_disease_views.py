from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import MortalStats, SettlementStats, SpeciesStats
from aerona.engine.demography.cohorts import seed
from aerona.engine.disease.control import DiseaseDesign, create_disease, loose
from tests.api.conftest import ApiWorld, seeded
from tests.engine.core.factories import entity
from tests.engine.society.factories import context


async def test_the_disease_card_shows_vector_targets_origin_hosts_and_holds(api: ApiWorld) -> None:
    core = seeded(api).core
    region = core.regions[0]
    async with api.services.database.write() as session:
        rats = await entity(session, "Bog Rats", EntityType.SPECIES, SpeciesStats(), world_id=core.world.id)
        ctx = context(session)
        design = DiseaseDesign(
            name="The Bog Ague", values={"primary_route": "bite", "target_functions": ["vital", "cognition"], "incubation": 4, "host_species_id": rats.id}
        )
        disease = await create_disease(ctx, region.id, design, son_id=None)
        await loose(ctx, region.id, disease_id=disease.id, severity=40, son_id=None)
        disease_id = disease.id
    view = (await api.http.get(f"/api/entities/{disease_id}/disease")).json()
    assert view["primary_route"] == "bite" and view["target_functions"] == ["cognition", "vital"]
    assert view["origin"] is not None and view["origin_incident_id"] == view["origin"]["id"]
    assert [host["name"] for host in view["hosts"]] == ["Bog Rats"] and view["hosts"][0]["primary"]
    assert "host_species_id" in view["locked"]
    assert view["unseen_pct"] > 0
    assert view["outbreaks"] and "locked" in view["outbreaks"][0]


async def test_demography_shows_sick_afflictions_and_named_mortals(api: ApiWorld) -> None:
    core = seeded(api).core
    region = core.regions[0]
    async with api.services.database.write() as session:
        town = await entity(
            session, "Fevertown", EntityType.SETTLEMENT, SettlementStats(population=3000, prosperity=50), world_id=core.world.id, location_id=region.id
        )
        await entity(session, "Ansel", EntityType.MORTAL, MortalStats(hp=100), world_id=core.world.id, location_id=town.id)
        ctx = context(session)
        await seed(session, ctx.rules, town, 3)
        disease = await create_disease(ctx, region.id, DiseaseDesign(values={"primary_route": "inhalation", "target_functions": ["breath"]}), son_id=None)
        await loose(ctx, town.id, disease_id=disease.id, severity=60, son_id=None)
        town_id = town.id
    view = (await api.http.get(f"/api/entities/{town_id}/demography")).json()
    assert [item["disease"] for item in view["afflictions"]]
    assert [item["name"] for item in view["named"]] == ["Ansel"]
    assert view["held"] == []
