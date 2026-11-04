from sqlalchemy import select

from aerona.db.tables.ecology import HerdRow
from aerona.db.tables.environment import PlaceEnvironmentRow, RegionEnvironmentRow
from aerona.db.tables.polity import PolityMemberRow, PolityTerritoryRow
from aerona.db.tables.region import PolityMapKnowledgeRow, RegionDangerRow, RegionHazardRow, RegionMemoryRow
from aerona.db.tables.warfare import BattleRow, WarRow
from aerona.domain.enums.ecology import DomesticationStage
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.environment import PlaceCover, RiverClass, ScarKind, SoilKind, TerrainKind, WaterSource
from aerona.domain.enums.region import DangerHarm, DangerOrigin, DangerSource, RegionMemoryKind, TerrainHazard
from aerona.domain.enums.war import BattleOutcome, WarCause, WarStatus
from aerona.domain.models.entity_stats import ArmyStats, EventStats, PlaceStats, PolityStats, SpeciesStats
from aerona.engine.environment import region_control
from aerona.engine.environment.control import set_biome, set_region_field, set_scar
from aerona.engine.environment.dangers import harm_of, weighted
from aerona.engine.environment.hazards import HazardTally, strike
from aerona.engine.environment.memory import darkness
from aerona.engine.environment.perils import haunt_factor, navigate
from aerona.engine.phases.environment import decay_scars, land_use
from aerona.engine.phases.regions import danger_harm, region_survey, sacred_pilgrims
from aerona.engine.phases.travel import road_risk
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.environment.factories import mapped_region
from tests.engine.environment.test_environment import surveyed
from tests.engine.society.factories import Realm, context, make, mortal, people, settlement, store_map, tuned

RULES = Rules()


async def dangers_of(realm: Realm, region_id: int) -> dict[DangerSource, RegionDangerRow]:
    rows = await realm.session.scalars(select(RegionDangerRow).where(RegionDangerRow.region_entity_id == region_id))
    return {row.source: row for row in rows}


async def test_danger_is_typed_by_its_sources_and_sums_into_the_stat(realm: Realm) -> None:
    ground = await surveyed(realm)
    set_region_field(ground, "dominant_terrain", TerrainKind.MARSH.value, lock=True)
    set_region_field(ground, "disease_load", 80, lock=True)
    set_region_field(ground, "wetland", 60, lock=True)
    await people(realm, "Fen Folk")
    await mortal(realm, "Red Hand", role=MortalRole.BANDIT)
    await region_survey(context(realm.session))
    found = await dangers_of(realm, realm.region.id)
    assert {DangerSource.QUICKSAND, DangerSource.DISEASE, DangerSource.BANDITS} <= set(found)
    assert found[DangerSource.QUICKSAND].strength == RULES.regional_danger.quicksand_marsh + 60 * RULES.regional_danger.quicksand_wetland_pct // 100
    assert stat(realm.region, "danger") == min(100, sum(row.strength for row in found.values()))
    assert all(row.origin is DangerOrigin.DERIVED for row in found.values())


async def test_a_held_danger_stays_and_a_released_curse_fades_back_to_the_land(realm: Realm) -> None:
    await surveyed(realm)
    epoch = 3
    held = await region_control.set_danger(realm.session, RULES, realm.region.id, DangerSource.MONSTERS, 70, epoch=epoch, held=True)
    cursed = await region_control.set_danger(
        realm.session, RULES, realm.region.id, DangerSource.VOLCANIC, 50, epoch=epoch, held=False, origin=DangerOrigin.DIVINE
    )
    await region_survey(context(realm.session))
    assert held.strength == 70 and held.held
    assert cursed.strength == 50 - RULES.regional_danger.curse_fade and cursed.origin is DangerOrigin.DIVINE
    await region_control.release_danger(realm.session, RULES, held.id)
    for epoch_ in range(4, 40):
        await region_survey(context(realm.session, epoch=epoch_))
    assert DangerSource.MONSTERS not in await dangers_of(realm, realm.region.id)
    assert DangerSource.VOLCANIC not in await dangers_of(realm, realm.region.id)


async def test_dangers_take_settlers_and_herds(realm: Realm) -> None:
    await surveyed(realm)
    town = await settlement(realm, "Lowmere", population=10000)
    beast = await make(
        realm.session, "Wolf", EntityType.SPECIES, SpeciesStats(hp=40, strength=40, agility=60, intelligence=10, danger=40, abundance=50), world_id=realm.world.id
    )
    realm.session.add(HerdRow(community_entity_id=town.id, species_entity_id=beast.id, head=1000, stage=DomesticationStage.HERDED))
    await region_control.set_danger(realm.session, RULES, realm.region.id, DangerSource.BEASTS, 100, epoch=3, held=True)
    await danger_harm(context(realm.session))
    herd = await realm.session.get(HerdRow, (town.id, beast.id))
    assert herd is not None and herd.head < 1000
    assert (stat(town, "population") or 0) < 10000


async def test_armies_lose_men_and_fall_into_ambush_and_travellers_pay_the_land(realm: Realm) -> None:
    await surveyed(realm)
    await region_control.set_danger(realm.session, RULES, realm.region.id, DangerSource.BANDITS, 100, epoch=3, held=True)
    rows = list(await realm.session.scalars(select(RegionDangerRow)))
    assert weighted(RULES, rows, DangerHarm.AMBUSH) == RULES.regional_danger.bandits_ambush
    assert await harm_of(realm.session, RULES, realm.region.id, DangerHarm.TRAVELLERS) == RULES.regional_danger.bandits_travellers
    route = type("Route", (), {"danger": 0})()
    calm = road_risk(RULES, route, set(), None)  # type: ignore[arg-type]
    risky = road_risk(RULES, route, set(), None, region_danger=90)  # type: ignore[arg-type]
    assert risky > calm


async def test_an_army_loses_its_way_in_land_its_realm_never_mapped(realm: Realm) -> None:
    await surveyed(realm)
    home = await people(realm, "Marchers", location_id=realm.far_region.id)
    realm_entity = await make(realm.session, "Kingdom", EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    realm.session.add(PolityMemberRow(polity_entity_id=realm_entity.id, member_entity_id=home.id))
    army = await make(realm.session, "Host", EntityType.ARMY, ArmyStats(size=1000), world_id=realm.world.id)
    rules = tuned(RULES, terrain={"lost_chance_pct": 100})
    ctx = context(realm.session, rules)
    lost = await navigate(ctx, army, home, realm.region.id, realm.far_region.id, charted=False)
    assert lost.lost and lost.dead == 1000 * rules.terrain.lost_attrition_pct // 100
    await region_control.set_knowledge(realm.session, realm_entity.id, realm.region.id, 90, held=True, epoch=3)
    assert not (await navigate(ctx, army, home, realm.region.id, realm.far_region.id, charted=False)).lost


async def test_realms_chart_their_land_and_neighbours_and_held_maps_stay(realm: Realm) -> None:
    await surveyed(realm)
    polity = await make(realm.session, "Kingdom", EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    realm.session.add(PolityTerritoryRow(polity_entity_id=polity.id, region_entity_id=realm.region.id, control=80))
    await realm.session.flush()
    await region_survey(context(realm.session))
    own = await realm.session.get(PolityMapKnowledgeRow, (polity.id, realm.region.id))
    near = await realm.session.get(PolityMapKnowledgeRow, (polity.id, realm.far_region.id))
    assert own is not None and own.level == RULES.terrain.knowledge_owned
    assert near is not None and near.level == RULES.terrain.knowledge_neighbour
    await region_control.set_knowledge(realm.session, polity.id, realm.far_region.id, 5, held=True, epoch=3)
    await region_survey(context(realm.session, epoch=4))
    assert near.level == 5
    await region_control.release_knowledge(realm.session, polity.id, realm.far_region.id)
    await region_survey(context(realm.session, epoch=5))
    assert near.level == RULES.terrain.knowledge_neighbour


async def test_the_land_remembers_battles_and_dark_memories_raise_hauntings(realm: Realm) -> None:
    await surveyed(realm)
    first = await people(realm, "North")
    second = await people(realm, "South")
    event = await make(realm.session, "The Long War", EntityType.EVENT, EventStats(severity=50), world_id=realm.world.id)
    war = WarRow(event_entity_id=event.id, cause=WarCause.HOSTILITY, status=WarStatus.ONGOING, started_epoch=2, world_id=realm.world.id)
    realm.session.add(war)
    await realm.session.flush()
    realm.session.add(
        BattleRow(
            war_id=war.id,
            epoch=2,
            sequence=1,
            place_entity_id=realm.region.id,
            winner_entity_id=first.id,
            loser_entity_id=second.id,
            outcome=BattleOutcome.SIEGE_BREACHED,
            gap=1.0,
            winner_losses=2000,
            loser_losses=3000,
        )
    )
    await realm.session.flush()
    calm = await haunt_factor(realm.session, RULES, realm.region.id)
    await region_survey(context(realm.session))
    memory = await realm.session.scalar(select(RegionMemoryRow).where(RegionMemoryRow.region_entity_id == realm.region.id))
    assert memory is not None and memory.kind is RegionMemoryKind.SACK and memory.magnitude >= RULES.terrain.memory_sack
    assert darkness(RULES, [memory]) > 0
    assert await haunt_factor(realm.session, RULES, realm.region.id) > calm
    await region_survey(context(realm.session, epoch=4))
    assert len(list(await realm.session.scalars(select(RegionMemoryRow)))) == 1


async def test_saints_graves_make_holy_ground_that_draws_pilgrims(realm: Realm) -> None:
    ground = await surveyed(realm)
    town = await settlement(realm, "Shrineford", prosperity=40)
    saint = await mortal(realm, "Blessed Ona", role=MortalRole.SAINT, location_id=town.id)
    saint.status = EntityStatus.DEAD
    saint.end_epoch = 2
    await realm.session.flush()
    rules = tuned(RULES, terrain={"memory_saint": 100, "sacred_memory_pct": 100, "pilgrim_sacred_min": 10})
    await region_survey(context(realm.session, rules))
    assert ground.sacredness >= 90
    await sacred_pilgrims(context(realm.session, rules))
    assert (stat(town, "prosperity") or 0) > 40
    await region_control.sanctify(realm.session, rules, realm.region.id, 12, held=True)
    await region_survey(context(realm.session, rules, epoch=4))
    assert ground.sacredness == 12


async def test_a_wildfire_strikes_hurts_the_named_and_burns_the_land(realm: Realm) -> None:
    ground = await surveyed(realm)
    town = await settlement(realm, "Pinecrest", population=10000)
    hunter = await mortal(realm, "Ash", location_id=town.id)
    ctx = context(realm.session)
    tally = HazardTally()
    await strike(ctx, await RegionAtlas.load(realm.session), ground, TerrainHazard.WILDFIRE, season=None, year=60, tally=tally)
    assert tally.strikes == 1 and tally.dead == 10000 * RULES.hazards.wildfire_deaths_permille // 1000
    assert ground.scars.get(ScarKind.BURNED.value) == RULES.hazards.wildfire_scar
    row = await realm.session.scalar(select(RegionHazardRow))
    assert row is not None and row.injured >= 1 and row.hazard is TerrainHazard.WILDFIRE
    assert (stat(hunter, "hp") or 100) < 100


async def test_a_river_turned_into_a_neighbour_dries_and_waters_places(realm: Realm) -> None:
    ground = await surveyed(realm, river=RiverClass.GREAT_RIVER)
    far = await realm.session.get(RegionEnvironmentRow, realm.far_region.id)
    assert far is not None
    await store_map(
        realm.session,
        realm.world.id,
        [
            mapped_region(realm.region.id, neighbours=[realm.far_region.id]),
            mapped_region(realm.far_region.id, neighbours=[realm.region.id], river=RiverClass.NONE),
        ],
    )
    far.river_class = RiverClass.NONE
    ground.river_class = RiverClass.GREAT_RIVER
    spring = await make(realm.session, "Old Ford", EntityType.PLACE, PlaceStats(), world_id=realm.world.id, location_id=realm.region.id)
    dry = await make(realm.session, "Dry Hollow", EntityType.PLACE, PlaceStats(), world_id=realm.world.id, location_id=realm.far_region.id)
    realm.session.add(
        PlaceEnvironmentRow(
            entity_id=spring.id, region_entity_id=realm.region.id, cover=PlaceCover.OPEN, water_source=WaterSource.RIVER, height_advantage=0, soil_fertility=40
        )
    )
    realm.session.add(
        PlaceEnvironmentRow(
            entity_id=dry.id, region_entity_id=realm.far_region.id, cover=PlaceCover.OPEN, water_source=WaterSource.NONE, height_advantage=0, soil_fertility=40
        )
    )
    await realm.session.flush()
    rules = tuned(RULES, terrain={"redirect_leaves_stream": 0})
    moved = await region_control.redirect_river(realm.session, rules, realm.region.id, realm.far_region.id)
    assert ground.river_class is RiverClass.NONE and far.river_class is RiverClass.GREAT_RIVER
    assert moved.dried == 1 and moved.watered == 1
    assert "river_class" in ground.locked and "river_class" in far.locked


async def test_held_soil_land_use_and_scars_survive_the_engine(realm: Realm) -> None:
    ground = await surveyed(realm)
    await people(realm, "Ploughmen", population=20000)
    for field, value in (("farmed", 5), ("erosion", 70), ("soil_fertility", 33), ("soil", SoilKind.SALT.value)):
        set_region_field(ground, field, value, lock=True)
    set_scar(ground, ScarKind.HAUNTED, 40, lock=True)
    set_biome(ground, 8, 70, lock=True)
    await land_use(context(realm.session))
    decay_scars(RULES, ground)
    assert (ground.farmed, ground.erosion, ground.soil_fertility, ground.soil) == (5, 70, 33, SoilKind.SALT)
    assert ground.scars[ScarKind.HAUNTED.value] == 40
    assert ground.biome_mix[8] == 70 and "biome_mix" in ground.locked
