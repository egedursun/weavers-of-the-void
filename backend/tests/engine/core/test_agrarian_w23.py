from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.agrarian_lines import mortal_agrarian_lines, son_agrarian_lines
from aerona.agents.context.scope import load_scope
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.agrarian import (
    BrandRow,
    CentralPlaceRow,
    CommonsRow,
    FamineLoreRow,
    GameReserveRow,
    IntensificationRow,
    KeystoneResourceRow,
    LandRingRow,
    PerennialRow,
    PreparednessRow,
    ReliefAidRow,
    SoilNutrientRow,
)
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.cycles import GiftRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.economy import ProductionRunRow, WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import NotableYearRow, RegionEnvironmentRow
from aerona.db.tables.intrigue import FavourRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import HouseProfileRow, OfficeRow, PolityMemberRow, PolityProfileRow, PolityTerritoryRow
from aerona.db.tables.regime import RegimeRow
from aerona.db.tables.settlement import SettlementInfrastructureRow, SettlementProfileRow
from aerona.domain.enums.agrarian import (
    AidKind,
    CentralityRank,
    CommonsKind,
    CommonsRule,
    KeystoneUse,
    LandUseRing,
    NutrientKind,
    PerennialKind,
    PreparednessKind,
    RebuildCause,
    RebuildPlan,
)
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.cycles import GiftOccasion
from aerona.domain.enums.economy import CommodityKind, WorkshopKind
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.environment import NotableYearKind, RiverClass
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.intrigue import FavourOrigin
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, OfficeKind
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.urban import Morphology
from aerona.domain.models.entity_stats import EventStats, HouseStats, PolityStats
from aerona.engine.agrarian.book import (
    Cushion,
    counted_people,
    cushioned,
    deposit,
    farming_boost,
    fell_plantings,
    gap_of,
    method_lift,
    nutrient_shift,
    readout,
    reserve_factor,
    reserve_marks,
    ring_shares,
    shield_of,
)
from aerona.engine.agrarian.control import designate_keystone, edit_record
from aerona.engine.agrarian.lands import Holdings, LandsTally, enclose, grow, holdings, keep_commons, keep_lands, keep_reserves, realm_dispossessed
from aerona.engine.agrarian.resilience import ResilienceTally, prepare, rebuild, relieve
from aerona.engine.agrarian.rings import SpatialTally, keep_spatial
from aerona.engine.agrarian.ruin import mark_ruin
from aerona.engine.agrarian.soil import SoilTally, feed_soils, keep_soil, press_land, remember_famines
from aerona.engine.agrarian.staples import StaplesTally, keep_brands, keep_keystones
from aerona.engine.context import TickContext
from aerona.engine.faith.book import FaithBook
from aerona.engine.phases.environment import environment_survey
from aerona.engine.polity.book import RealmBook
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import stat_or
from aerona.engine.services.community_relations import change_relation
from aerona.services.integrity.agrarian_links import mend_agrarian_links
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement, tuned_rules

BIG = 4000
SMALL = 600
EPOCHS = 12


async def surveyed(session: AsyncSession, **namespaces: dict[str, int]) -> TickContext:
    ctx = await manual_context(session, "agrarian", rules=tuned_rules(**namespaces))
    await environment_survey(ctx)
    return ctx


async def town(session: AsyncSession, world: CoreWorld, name: str, region: int, population: int, *, tier: SizeTier = SizeTier.TOWN) -> EntityRow:
    found = await settlement(session, name, world, world.regions[region], population=population)
    session.add(SettlementProfileRow(settlement_entity_id=found.id, size_tier=tier, treasury=2000, investment_pool=2000, locked=[], foreigners={}))
    session.add(SettlementInfrastructureRow(settlement_entity_id=found.id, roads=0, locked=[]))
    await session.flush()
    return found


async def land(session: AsyncSession, world: CoreWorld, region: int) -> RegionEnvironmentRow:
    found = await session.get(RegionEnvironmentRow, world.regions[region].id)
    assert found is not None
    return found


async def realm(session: AsyncSession, world: CoreWorld, towns: list[EntityRow], ruler: EntityRow | None, treasury: int = 4000) -> EntityRow:
    polity = await entity(session, f"Crown of {towns[0].name}", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(
        PolityProfileRow(
            polity_entity_id=polity.id,
            government=GovernmentKind.MONARCHY,
            decision_rule=DecisionRule.AUTOCRATIC,
            capital_entity_id=towns[0].id,
            core_entity_id=polity.id,
            legitimacy=50,
            stability=50,
            treasury=treasury,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    for member in towns:
        session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=member.id))
    if ruler is not None:
        session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id, since_epoch=0, powers=[], locked=[]))
    await session.flush()
    return polity


async def test_rings_follow_the_cost_of_carrying_and_a_river_stretches_them(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session, central_places={"weekly_threshold": 1000})
    await town(session, world, "Hollin", 0, BIG)
    tally = SpatialTally()
    await keep_spatial(ctx, tally)
    rings = [await session.get(LandRingRow, region.id) for region in world.regions]
    assert all(row is not None for row in rings)
    assert [row.ring for row in rings if row is not None] == [LandUseRing.GARDENS, LandUseRing.GRAIN, LandUseRing.GRAIN, LandUseRing.RANCHING]
    assert tally.markets == 1
    for index in range(4):
        (await land(session, world, index)).river_class = RiverClass.RIVER
    await keep_spatial(ctx, SpatialTally())
    far = await session.get(LandRingRow, world.regions[3].id)
    assert far is not None and far.ring is LandUseRing.GRAIN and far.by_water
    near = await session.get(LandRingRow, world.regions[1].id)
    assert near is not None and near.ring is LandUseRing.FORESTRY
    assert ring_shares(ctx.rules, LandUseRing.RANCHING)[0] < ring_shares(ctx.rules, LandUseRing.GRAIN)[0]
    assert ring_shares(ctx.rules, LandUseRing.RANCHING)[1] > ring_shares(ctx.rules, LandUseRing.GRAIN)[1]


async def test_central_places_rank_by_their_buyers_and_leave_gaps_for_founders(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session, central_places={"weekly_threshold": 1000, "rare_threshold": 100000, "gap_from": 50, "gap_span": 100})
    big = await town(session, world, "Hollin", 0, BIG)
    small = await town(session, world, "Brack", 0, SMALL, tier=SizeTier.VILLAGE)
    await keep_spatial(ctx, SpatialTally())
    market, hamlet = await session.get(CentralPlaceRow, big.id), await session.get(CentralPlaceRow, small.id)
    assert market is not None and hamlet is not None
    assert market.rank is CentralityRank.WEEKLY and hamlet.rank is CentralityRank.DAILY
    assert hamlet.served_by_entity_id == big.id
    assert market.centrality > hamlet.centrality
    assert counted_people(ctx.rules, BIG, market.centrality) > BIG
    assert await gap_of(session, world.regions[3].id) > await gap_of(session, world.regions[0].id)
    await edit_record(ctx, "central_place", small.id, {"rank": CentralityRank.RARE.value}, [])
    await keep_spatial(ctx, SpatialTally())
    held_rank = await session.get(CentralPlaceRow, small.id)
    assert held_rank is not None and held_rank.rank is CentralityRank.RARE


async def test_pressure_on_the_land_drives_harder_farming_research_and_methods(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session, boserup={"onset": 0, "drift_pct": 100})
    crowded = await town(session, world, "Hollin", 0, BIG * 10)
    tally = SoilTally()
    await press_land(ctx, tally)
    row = await session.get(IntensificationRow, world.regions[0].id)
    assert row is not None and row.pressure > 0 and row.intensity > 0 and row.research_boost > 0
    assert await farming_boost(session, crowded) > 1.0
    assert await method_lift(session, ctx.rules, crowded) > 1.0


async def test_crops_draw_the_soil_and_watered_fields_salt_without_drainage(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session)
    farmland = await town(session, world, "Hollin", 0, BIG)
    ground = await land(session, world, 0)
    ground.farmed, ground.cleared, ground.grazed, ground.forest_cover = 80, 85, 0, 0
    infrastructure = await session.get(SettlementInfrastructureRow, farmland.id)
    assert infrastructure is not None
    infrastructure.irrigation = 3
    await session.flush()
    atlas = await RegionAtlas.load(session)
    tally = SoilTally()
    for _ in range(EPOCHS):
        await feed_soils(ctx, atlas, tally)
    salt = await session.get(SoilNutrientRow, (ground.entity_id, NutrientKind.SALINITY))
    fixed = await session.get(SoilNutrientRow, (ground.entity_id, NutrientKind.FIXED))
    assert salt is not None and fixed is not None
    assert salt.stock >= ctx.rules.nutrients.noted_salinity and tally.salted == 1
    assert fixed.stock < ground.soil_base
    stocks = {row.nutrient: row.stock for row in await session.scalars(select(SoilNutrientRow).where(SoilNutrientRow.region_entity_id == ground.entity_id))}
    assert nutrient_shift(ctx.rules, stocks, ground.soil_base) < 0
    session.add(HolderTechniqueRow(holder_entity_id=farmland.id, technique=Technique.DRAINAGE, since_epoch=0))
    await session.flush()
    before = salt.stock
    await feed_soils(ctx, atlas, SoilTally())
    assert salt.stock < before
    mineral = await session.get(SoilNutrientRow, (ground.entity_id, NutrientKind.MINERAL))
    assert mineral is not None
    rich = mineral.stock
    await deposit(ctx, ground.entity_id, NutrientKind.MINERAL, 10)
    assert mineral.stock == min(100, rich + 10)
    assert readout(ctx.rules, {NutrientKind.FIXED: 60, NutrientKind.MINERAL: 60, NutrientKind.ORGANIC: 60, NutrientKind.SALINITY: 50}) == 30


async def test_plantings_bear_after_epochs_pay_their_owner_and_fall_to_war(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session)
    owner = await town(session, world, "Hollin", 0, BIG)
    row = PerennialRow(region_entity_id=world.regions[0].id, kind=PerennialKind.ORCHARD, owner_node_id=owner.id, area=10, mature_epochs=2, locked=[])
    session.add(row)
    await session.flush()
    profile = await session.get(SettlementProfileRow, owner.id)
    assert profile is not None
    lands = await holdings(ctx)
    tally = LandsTally()
    for _ in range(3):
        await grow(ctx, lands, tally)
    assert row.maturity == 100 and tally.bearing >= 1
    assert await fell_plantings(ctx, world.regions[0], ctx.rules.perennials.felling_pct) == 1
    assert row.maturity == 50 and row.felled_epoch == ctx.epoch and row.condition < 100


async def test_an_overused_common_wears_down_and_its_enclosure_fills_the_city(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session, commons={"enclose_pct": 100, "council_chance": 0})
    village = await town(session, world, "Brack", 1, BIG, tier=SizeTier.VILLAGE)
    city = await town(session, world, "Hollin", 3, BIG, tier=SizeTier.CITY)
    ruler = await mortal(session, "Ruler", world, city.id)
    crown = await realm(session, world, [city, village], ruler)
    session.add(IntensificationRow(region_entity_id=world.regions[1].id, pressure=150, locked=[]))
    common = CommonsRow(region_entity_id=world.regions[1].id, kind=CommonsKind.PASTURE, steward_entity_id=village.id, condition=80, locked=[])
    session.add(common)
    await session.flush()
    people_before, city_before = stat_or(village, "population", 0), stat_or(city, "population", 0)
    tally = LandsTally()
    await keep_commons(ctx, await holdings(ctx), tally)
    assert common.condition < 80
    assert common.rule is CommonsRule.ENCLOSED and common.encloser_node_id == ruler.id and common.dispossessed > 0
    assert stat_or(village, "population", 0) < people_before and stat_or(city, "population", 0) > city_before
    profile = await session.get(SettlementProfileRow, village.id)
    assert profile is not None and profile.unrest > 10
    book = await RealmBook.load(session)
    assert realm_dispossessed([common], book, crown.id) == common.dispossessed
    calm = await session.scalar(select(CommonsRow).where(CommonsRow.region_entity_id == world.regions[1].id, CommonsRow.kind == CommonsKind.WOODS))
    if calm is None:
        calm = CommonsRow(region_entity_id=world.regions[1].id, kind=CommonsKind.WOODS, steward_entity_id=village.id, locked=[])
        session.add(calm)
    calm.rule, calm.condition = CommonsRule.COUNCIL, 80
    await session.flush()
    ctx = await surveyed(session, commons={"enclose_pct": 0})
    await keep_commons(ctx, await holdings(ctx), LandsTally())
    assert calm.condition > 80 - (150 - ctx.rules.commons.sustainable) * ctx.rules.commons.degrade_pct / 100


async def test_a_reserve_shields_its_game_and_the_hungry_poach_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session, game_laws={"drift_pct": 100, "punish_at": 10})
    hollin = await town(session, world, "Hollin", 0, BIG)
    lord = await mortal(session, "Lord", world, hollin.id)
    reserve = GameReserveRow(region_entity_id=world.regions[0].id, holder_node_id=lord.id, strictness=60, locked=[])
    session.add(reserve)
    (await land(session, world, 0)).harvest_pct = 20
    await session.flush()
    await keep_reserves(ctx, await holdings(ctx), LandsTally())
    assert reserve.poaching > 0 and reserve.resentment > 0
    profile = await session.get(SettlementProfileRow, hollin.id)
    assert profile is not None and profile.crime > 10
    marks = await reserve_marks(session)
    assert reserve_factor(ctx.rules, marks, world.species.id, world.regions[0].id) < 1.0
    assert reserve_factor(ctx.rules, marks, world.species.id, world.regions[1].id) == 1.0


async def test_remembered_hunger_teaches_famine_foods_and_stores_cushion_a_failed_harvest(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session, famine_foods={"drift_pct": 100})
    hollin = await town(session, world, "Hollin", 0, BIG)
    await BondRepository(session).connect(BondDraft(world.people.id, hollin.id, BondKind.LIVES_IN, 0))
    for year in range(3):
        session.add(
            NotableYearRow(
                world_id=world.world.id,
                region_entity_id=world.regions[0].id,
                epoch=ctx.epoch,
                year=year,
                kind=NotableYearKind.HUNGER,
                name=f"Hungry Year {year}",
                magnitude=60,
            )
        )
    await session.flush()
    tally = SoilTally()
    await remember_famines(ctx, await RegionAtlas.load(session), tally)
    lore = await session.get(FamineLoreRow, world.people.id)
    assert lore is not None and lore.famine_foods and lore.storage > 0 and tally.famine_foods == 1
    fed, foraged = cushioned(ctx.rules, 20, Cushion(lore.storage, lore.famine_foods))
    assert fed > 20 and foraged
    assert cushioned(ctx.rules, 90, Cushion(lore.storage, True)) == (90, False)


async def test_works_hold_back_a_flood_and_towns_build_what_they_remember(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session)
    hollin = await town(session, world, "Hollin", 0, BIG)
    (await land(session, world, 0)).river_class = RiverClass.RIVER
    flood = await entity(session, "The Flood", EntityType.EVENT, EventStats(severity=60), world_id=world.world.id, location_id=hollin.id)
    flood.engine_kind = EngineKind.FLOOD
    flood.birth_epoch = ctx.epoch
    await session.flush()
    tally = ResilienceTally()
    await prepare(ctx, await RegionAtlas.load(session), tally)
    levee = await session.get(PreparednessRow, (hollin.id, PreparednessKind.LEVEE))
    assert levee is not None and levee.level == 1 and tally.raised == 1
    levee.level = 4
    cut = await shield_of(ctx, hollin, Disaster.FLOOD)
    assert cut > 0 and levee.averted == 1
    assert await shield_of(ctx, hollin, Disaster.EARTHQUAKE) < cut


async def test_aid_earns_a_favour_and_a_gift_owed_and_a_rival_turns_it_away(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session, relief={"chance_pct": 100})
    stricken = await town(session, world, "Brack", 1, BIG)
    lord = await mortal(session, "Lord", world, stricken.id)
    session.add(MortalProfileRow(entity_id=lord.id, honour=50, locked=[]))
    own = await realm(session, world, [stricken], lord)
    helper = await town(session, world, "Hollin", 3, BIG)
    giver = await realm(session, world, [helper], None)
    flood = await entity(session, "The Flood", EntityType.EVENT, EventStats(severity=60), world_id=world.world.id, location_id=stricken.id)
    flood.engine_kind = EngineKind.FLOOD
    flood.birth_epoch = ctx.epoch
    await session.flush()
    tally = ResilienceTally()
    await relieve(ctx, await RegionAtlas.load(session), tally)
    aid = await session.scalar(select(ReliefAidRow).where(ReliefAidRow.giver_node_id == giver.id))
    assert aid is not None and not aid.refused and aid.kind is AidKind.GOODS and tally.aid == 1
    assert await session.scalar(select(FavourRow).where(FavourRow.owed_to_node_id == giver.id, FavourRow.origin == FavourOrigin.RELIEF)) is not None
    assert await session.scalar(select(GiftRow).where(GiftRow.giver_node_id == giver.id, GiftRow.occasion == GiftOccasion.RELIEF)) is not None
    await change_relation(ctx, own.id, giver.id, -90, MemoryKind.HARMED_ME, note="an old war")
    honour = await session.get(MortalProfileRow, lord.id)
    assert honour is not None
    before = honour.honour
    tally = ResilienceTally()
    await relieve(ctx, await RegionAtlas.load(session), tally)
    assert tally.refused == 1
    after = await session.get(MortalProfileRow, lord.id)
    assert after is not None and after.honour < before


async def test_a_burned_town_rebuilds_in_haste_and_an_elite_seizes_the_burned_land(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session, reconstruction={"seize_pct": 100})
    hollin = await town(session, world, "Hollin", 0, BIG)
    house = await entity(session, "House Morrow", EntityType.HOUSE, HouseStats(), world_id=world.world.id)
    session.add(HouseProfileRow(house_entity_id=house.id, wealth=60, seats=[hollin.id], locked=[]))
    await session.flush()
    row = await mark_ruin(ctx, hollin, RebuildCause.FIRE)
    assert row is not None and await mark_ruin(ctx, hollin, RebuildCause.FLOOD) is row
    tally = ResilienceTally()
    await rebuild(ctx, tally)
    assert row.plan is RebuildPlan.OPPORTUNISTIC and row.cost > 0 and row.seized_by_node_id == house.id and row.seized > 0 and tally.seized == 1
    profile = await session.get(SettlementProfileRow, hollin.id)
    assert profile is not None and profile.homeless >= row.seized
    await rebuild(ctx, ResilienceTally())
    assert row.finished_epoch == ctx.epoch
    assert profile.morphology.value == Morphology.ORGANIC.value
    planned = await mark_ruin(ctx, hollin, RebuildCause.QUAKE)
    assert planned is not None
    await edit_record(ctx, "reconstruction", planned.id, {"plan": RebuildPlan.PLANNED.value, "cost": 100, "paid": 100}, [])
    for _ in range(4):
        await rebuild(ctx, ResilienceTally())
    assert planned.finished_epoch == ctx.epoch and profile.morphology is Morphology.PLANNED


async def test_a_keystone_thins_its_producers_enriches_its_holder_and_brings_war_when_scarce(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session, keystone_resource={"harm_pct": 100, "war_pct": 100, "envy_at": 100, "envy": 0})
    source = world.regions[0]
    session.add(SpeciesRangeRow(species_entity_id=world.species.id, region_entity_id=source.id, abundance=20, fit=100, since_epoch=0, locked=[]))
    hollin = await town(session, world, "Hollin", 0, BIG)
    rival_town = await town(session, world, "Brack", 2, BIG)
    holder = await realm(session, world, [hollin], None, treasury=100)
    rival = await realm(session, world, [rival_town], None)
    session.add(PolityTerritoryRow(polity_entity_id=holder.id, region_entity_id=source.id, control=80, locked=[]))
    await session.flush()
    row = await designate_keystone(ctx, world.world.id, "The First Yield", use=KeystoneUse.PRESCIENCE, producer_id=world.species.id, source_id=source.id)
    row.locked = []
    row.harvest = 60
    await session.flush()
    tally = StaplesTally()
    await keep_keystones(ctx, await RegionAtlas.load(session), *(await faith_and_book(session)), tally)
    found = await session.get(SpeciesRangeRow, (world.species.id, source.id))
    assert found is not None and found.abundance < 20
    assert row.controller_entity_id == holder.id and row.supply < ctx.rules.keystone_resource.scarce_at and row.price > 100
    profile = await session.get(PolityProfileRow, holder.id)
    assert profile is not None and profile.treasury > 100 and tally.scarce == 1
    assert tally.wars == 1 and rival.id != holder.id
    assert await session.scalar(select(KeystoneResourceRow.id).where(KeystoneResourceRow.world_id == world.world.id)) == row.id


async def faith_and_book(session: AsyncSession) -> tuple[FaithBook, RealmBook]:
    return await FaithBook.load(session), await RealmBook.load(session)


async def test_a_workshop_of_fine_work_earns_a_brand_that_passes_with_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session, brands={"drift_pct": 100})
    hollin = await town(session, world, "Hollin", 0, BIG)
    smith = await mortal(session, "Smith", world, hollin.id)
    heir = await mortal(session, "Heir", world, hollin.id)
    shop = WorkshopRow(community_entity_id=hollin.id, kind=WorkshopKind.FORGE, level=3, built_epoch=0, owner_node_id=smith.id)
    session.add(shop)
    await session.flush()
    session.add(
        ProductionRunRow(
            epoch=ctx.epoch, community_entity_id=hollin.id, step="smithing", workshop=WorkshopKind.FORGE, output=CommodityKind.TOOLS, quantity=20, quality=90
        )
    )
    await session.flush()
    tally = StaplesTally()
    await keep_brands(ctx, tally)
    brand = await session.scalar(select(BrandRow).where(BrandRow.workshop_id == shop.id))
    assert brand is not None and tally.earned == 1 and brand.owner_node_id == smith.id and brand.reputation > 10
    shop.owner_node_id = heir.id
    await keep_brands(ctx, StaplesTally())
    assert brand.owner_node_id == heir.id


async def test_the_salt_of_ages(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session, boserup={"onset": 0, "drift_pct": 100}, commons={"enclose_pct": 50, "council_chance": 0})
    village = await town(session, world, "Riverside", 1, BIG * 10, tier=SizeTier.VILLAGE)
    city = await town(session, world, "Hollin", 3, BIG, tier=SizeTier.CITY)
    usurper = await mortal(session, "Usurper", world, city.id)
    crown = await realm(session, world, [city, village], usurper)
    session.add(RegimeRow(polity_entity_id=crown.id, horizon=10, locked=[]))
    ground = await land(session, world, 1)
    ground.farmed, ground.cleared, ground.grazed = 80, 85, 20
    infrastructure = await session.get(SettlementInfrastructureRow, village.id)
    assert infrastructure is not None
    infrastructure.irrigation = 4
    await session.flush()
    tally = SoilTally()
    for _ in range(EPOCHS):
        await keep_soil(ctx, tally)
    pressed = await session.get(IntensificationRow, ground.entity_id)
    salt = await session.get(SoilNutrientRow, (ground.entity_id, NutrientKind.SALINITY))
    assert pressed is not None and pressed.intensity > 0 and pressed.research_boost > 0
    assert salt is not None and salt.stock >= ctx.rules.nutrients.noted_salinity
    stocks = {row.nutrient: row.stock for row in await session.scalars(select(SoilNutrientRow).where(SoilNutrientRow.region_entity_id == ground.entity_id))}
    assert nutrient_shift(ctx.rules, stocks, ground.soil_base) < 0
    city_before = stat_or(city, "population", 0)
    for _ in range(EPOCHS):
        await keep_lands(ctx, LandsTally())
    common = await session.scalar(select(CommonsRow).where(CommonsRow.region_entity_id == ground.entity_id, CommonsRow.kind == CommonsKind.PASTURE))
    assert common is not None and common.rule is CommonsRule.ENCLOSED and common.encloser_node_id == usurper.id
    assert stat_or(city, "population", 0) > city_before


async def test_agents_read_their_land_and_the_world_keystone(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session, central_places={"weekly_threshold": 1000})
    hollin = await town(session, world, "Hollin", 0, BIG)
    farmer = await mortal(session, "Farmer", world, hollin.id)
    await keep_spatial(ctx, SpatialTally())
    await feed_soils(ctx, await RegionAtlas.load(session), SoilTally())
    session.add(CommonsRow(region_entity_id=world.regions[0].id, kind=CommonsKind.WOODS, locked=[]))
    session.add(PreparednessRow(settlement_entity_id=hollin.id, kind=PreparednessKind.FIREBREAK, level=2, locked=[]))
    await designate_keystone(ctx, world.world.id, "The First Yield", use=KeystoneUse.RITE, source_id=world.regions[0].id)
    await session.flush()
    scope = await load_scope(session, ctx.rules)
    lines = await mortal_agrarian_lines(scope, farmer)
    assert any("ring" in line for line in lines) and any("common woods" in line for line in lines)
    assert any("firebreak level 2" in line for line in lines) and any("depends on" in line for line in lines)
    assert any("depends on" in line for line in await son_agrarian_lines(scope, world.son))


async def test_vanished_towns_and_peoples_lose_their_records(session: AsyncSession, world: CoreWorld) -> None:
    await surveyed(session)
    hollin = await town(session, world, "Hollin", 0, BIG)
    session.add(CentralPlaceRow(settlement_entity_id=hollin.id, locked=[]))
    session.add(FamineLoreRow(people_entity_id=world.people.id, locked=[]))
    await session.flush()
    hollin.status = EntityStatus.DESTROYED
    hollin.end_epoch = 2
    world.people.status = EntityStatus.DEAD
    world.people.end_epoch = 2
    await session.flush()
    assert await mend_agrarian_links(session) >= 2
    assert await session.get(CentralPlaceRow, hollin.id) is None and await session.get(FamineLoreRow, world.people.id) is None


async def test_enclosure_can_be_ordered_by_a_god(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session)
    village = await town(session, world, "Brack", 1, BIG, tier=SizeTier.VILLAGE)
    lord = await mortal(session, "Lord", world, village.id)
    common = CommonsRow(region_entity_id=world.regions[1].id, kind=CommonsKind.FISHERY, steward_entity_id=village.id, locked=[])
    session.add(common)
    await session.flush()
    lands: Holdings = await holdings(ctx)
    driven = await enclose(ctx, lands, common, lord, await RealmBook.load(session))
    assert driven > 0 and common.rule is CommonsRule.ENCLOSED and common.encloser_node_id == lord.id
