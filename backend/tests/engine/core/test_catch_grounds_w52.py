from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.catch import GEAR
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.agrarian import GameReserveRow
from aerona.db.tables.crafts import CatchGroundRow
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.crafts import CatchGround, Gear
from aerona.domain.enums.ecology import SizeClass
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import ScarKind, TemperatureBand
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.models.entity_stats import SpeciesStats
from aerona.engine.context import TickContext
from aerona.engine.crafts.grounds import GroundTally, hunt_game, keep_grounds
from aerona.engine.crafts.shores import open_ground, work_beds, work_ponds, work_shore
from aerona.engine.economy.stocks import goods_of, holdings
from aerona.engine.phases.environment import environment_survey
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.numbers import round_half_up
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules

RULES = Rules()


async def at(session: AsyncSession, epoch: int, **rules: dict[str, int]) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "crafts", rules=tuned_rules(**rules))


async def home(session: AsyncSession, world: CoreWorld) -> EntityRow:
    town = await settlement(session, "Shellhaven", world, world.regions[0])
    await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
    session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN))
    await session.flush()
    return town


async def kind(session: AsyncSession, world: CoreWorld, name: str, **profile: object) -> EntityRow:
    found = await entity(session, name, EntityType.SPECIES, SpeciesStats(hp=30, intelligence=10), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(SpeciesProfileRow(species_entity_id=found.id, **profile))
    session.add(SpeciesRangeRow(species_entity_id=found.id, region_entity_id=world.regions[0].id, abundance=60, hunted=5, locked=[]))
    await session.flush()
    return found


async def test_hunted_kinds_open_grounds_by_their_size_and_their_body(session: AsyncSession, world: CoreWorld) -> None:
    await environment_survey(await at(session, 2))
    big = await kind(session, world, "Tall Elk", size_class=SizeClass.LARGE)
    winged = await kind(session, world, "Reed Duck", body_plan=BodyPlan.AVIAN)
    small = await kind(session, world, "Hedge Hare", size_class=SizeClass.SMALL)
    await keep_grounds(await at(session, 3, grounds={"marine_hunt_chance": 0, "owned_chance": 0}), GroundTally())
    grounds = {row.source_entity_id: row for row in await session.scalars(select(CatchGroundRow))}
    assert grounds[big.id].ground is CatchGround.GAME_HUNT and grounds[winged.id].ground is CatchGround.FOWLING
    assert grounds[small.id].ground is CatchGround.TRAPPING


async def test_shores_beds_and_ponds_yield_their_goods(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    town = await home(session, world)
    region = world.regions[0].id
    shore = await open_ground(ctx, region, region, CatchGround.SHORE_GATHERING)
    beds = await open_ground(ctx, town.id, region, CatchGround.DIVING)
    assert shore is not None and beds is not None and await open_ground(ctx, region, region, CatchGround.SHORE_GATHERING) is None
    shore.effort = beds.effort = 50
    await work_shore(ctx, shore, town.id)
    assert shore.last_catch == round(RULES.grounds.shore_rate * GEAR[shore.gear].rate(RULES) / 100)
    assert shore.stock == min(100, 100 - round_half_up(RULES.grounds.shore_depletion * 50 / 100) + RULES.grounds.ground_regrow)
    await work_beds(await at(session, 3, grounds={"diving_death_pct": 0}), beds, town.id)
    stocks = await holdings(session, town.id)
    assert stocks.get(CommodityKind.FISH, 0) == shore.last_catch and stocks.get(CommodityKind.LUXURIES, 0) == beds.last_catch > 0
    pond = CatchGroundRow(
        source_entity_id=town.id, region_entity_id=world.regions[1].id, ground=CatchGround.FISH_PONDS, gear=Gear.NETS, first_stock=100, stock=100, locked=[]
    )
    session.add(pond)
    await goods_of(session, ctx.epoch).add(town.id, CommodityKind.GRAIN, RULES.grounds.pond_feed, GoodsFlow.EXTRACTION)
    await session.flush()
    await work_ponds(ctx, pond, town.id)
    assert pond.last_catch == RULES.grounds.pond_yield and (await holdings(session, town.id)).get(CommodityKind.GRAIN, 0) == 0


async def test_a_flood_ruins_the_ponds(session: AsyncSession, world: CoreWorld) -> None:
    await environment_survey(await at(session, 2))
    ctx = await at(session, 3)
    town = await home(session, world)
    pond = CatchGroundRow(
        source_entity_id=town.id, region_entity_id=world.regions[0].id, ground=CatchGround.FISH_PONDS, gear=Gear.NETS, first_stock=100, stock=100, locked=[]
    )
    session.add(pond)
    land = await session.get(RegionEnvironmentRow, world.regions[0].id)
    assert land is not None
    land.scars = {ScarKind.FLOODED.value: RULES.grounds.pond_flood_scar}
    await session.flush()
    await work_ponds(ctx, pond, town.id)
    assert pond.stock == 0 and "catch.ponds_ruined" in set(await session.scalars(select(IncidentRow.kind)))


async def test_a_diver_drowns_unless_the_people_breathe_under_water(session: AsyncSession, world: CoreWorld) -> None:
    town = await home(session, world)
    diver = await mortal(session, "Pearl Seeker", world, town.id)
    region = world.regions[0].id
    certain = await at(session, 3, grounds={"diving_death_pct": 100})
    beds = await open_ground(certain, town.id, region, CatchGround.DIVING)
    assert beds is not None
    session.add(
        PeopleBiologyRow(
            people_entity_id=world.people.id,
            maturity_years=16,
            adult_years=40,
            elder_years=65,
            fertility_pct=50,
            acclimatised=TemperatureBand.TEMPERATE,
            staple=CommodityKind.FISH,
            traits=[],
            body_plan=BodyPlan.AQUATIC,
            locked=[],
        )
    )
    await session.flush()
    await work_beds(certain, beds, town.id)
    assert diver.status is EntityStatus.CANON
    biology = await session.get(PeopleBiologyRow, world.people.id)
    assert biology is not None
    biology.body_plan = BodyPlan.HUMANOID
    await session.flush()
    await work_beds(await at(session, 4, grounds={"diving_death_pct": 100}), beds, town.id)
    assert "catch.diver_lost" in set(await session.scalars(select(IncidentRow.kind)))


async def test_a_hunt_of_large_game_feeds_its_towns_by_the_rule_save_what_a_reserve_keeps(session: AsyncSession, world: CoreWorld) -> None:
    town = await home(session, world)
    region = world.regions[0].id
    elk = await kind(session, world, "Tall Elk", size_class=SizeClass.LARGE)
    row = CatchGroundRow(source_entity_id=elk.id, region_entity_id=region, ground=CatchGround.GAME_HUNT, gear=Gear.MISSILES, first_stock=60, locked=[])
    session.add(row)
    await session.flush()
    full = round_half_up(40 * GEAR[Gear.MISSILES].rate(RULES) / 100)
    assert await hunt_game(await at(session, 3, grounds={"game_hunt_rate": 0}), row, [town.id]) == 0
    assert await hunt_game(await at(session, 3, grounds={"game_hunt_rate": 40}), row, [town.id]) == full
    await session.flush()
    assert (await holdings(session, town.id)).get(CommodityKind.MEAT, 0) == full
    assert row.last_catch == full
    session.add(GameReserveRow(region_entity_id=region, species_entity_id=elk.id, poaching=25, locked=[]))
    await session.flush()
    assert await hunt_game(await at(session, 3, grounds={"game_hunt_rate": 40}), row, [town.id]) == round_half_up(full * 25 / 100)
