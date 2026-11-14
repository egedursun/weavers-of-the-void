from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog import god_lines
from aerona.core.grammar import fill
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.cosmic_state import ResourceMechanicRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import RouteRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityType
from aerona.domain.enums.society import ResourceMechanic
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.models.entity_stats import PeopleStats, ResourceStats, StructureStats
from aerona.engine.gods.economy import cosmic_economy, found_faction, resource_mechanics
from aerona.engine.phases.god_power import spontaneous_curse, wrathful_pool
from aerona.rules.registry import Rules
from tests.engine.gods.factories import GodsWorld, add_world, bond, chronicle_keys, make_context, make_entity, make_son


def god_power(rules: Rules, **changes: int) -> Rules:
    return replace(rules, god_power=replace(rules.god_power, **changes))


def economy(rules: Rules, **changes: int) -> Rules:
    return replace(rules, economy=replace(rules.economy, **changes))


async def test_wrath_gathers_temple_breakers_the_cursed_and_killers(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    temple = await make_entity(session, "Salt Shrine", EntityType.STRUCTURE, world_id=world.world.id, engine_kind=EngineKind.TEMPLE, stats=StructureStats())
    breaker = await make_entity(session, "Brann", EntityType.MORTAL, world_id=world.world.id, power_level=2)
    cursed = await make_entity(session, "Ilsa", EntityType.MORTAL, world_id=world.world.id, power_level=5)
    killer = await make_entity(session, "Morv", EntityType.MORTAL, world_id=world.world.id, power_level=3)
    await bond(session, breaker.id, temple.id, BondKind.DESTROYED, 2)
    await EntityRepository(session).add_flag(cursed.id, EntityFlag.CURSED, 1)
    tuned = god_power(rules, auto_curse_min_kills=2, auto_curse_wrath_chance=100, auto_curse_chance=0, auto_candidates=1)
    for index in range(2):
        victim = await make_entity(session, f"Victim {index}", EntityType.MORTAL, world_id=world.world.id)
        await bond(session, killer.id, victim.id, BondKind.KILLED, 2)
    pool = await wrathful_pool(make_context(session, tuned, 3), world.creator, set())
    reasons = {candidate.mortal.id: candidate.reason for candidate in pool}
    assert reasons[breaker.id] == god_lines.CURSE_REASON_TEMPLE.format(creator=world.creator.name, place=temple.name)
    assert reasons[cursed.id] == god_lines.CURSE_REASON_CURSED
    assert reasons[killer.id] == fill(god_lines.CURSE_REASON_KILLER, count=2)
    world.creator.mood_anger = 100
    await spontaneous_curse(make_context(session, tuned, 3, "god_power"), world.creator)
    entities = EntityRepository(session)
    assert await entities.has_flag(cursed.id, EntityFlag.BLOODLINE_CURSE)
    assert not await entities.has_flag(breaker.id, EntityFlag.BLOODLINE_CURSE)
    assert god_lines.BLOODLINE_CURSE.key in await chronicle_keys(session)


async def test_a_calm_creator_curses_no_one_from_the_pool(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    cursed = await make_entity(session, "Ilsa", EntityType.MORTAL, world_id=world.world.id)
    await EntityRepository(session).add_flag(cursed.id, EntityFlag.CURSED, 1)
    world.creator.mood_anger = 0
    await spontaneous_curse(make_context(session, god_power(rules, auto_curse_wrath_chance=100), 3), world.creator)
    assert not await EntityRepository(session).has_flag(cursed.id, EntityFlag.BLOODLINE_CURSE)


async def test_digging_a_sacred_resource_angers_its_son_who_curses_the_owner(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    son = await make_son(session, "Velkar", world.world.id, wrath=20)
    resource = await make_entity(
        session, "Holy Vein", EntityType.RESOURCE, world_id=world.world.id, location_id=world.region.id, stats=ResourceStats(abundance=50)
    )
    resource.sacred_to_son_id = son.id
    session.add(ResourceMechanicRow(entity_id=resource.id, mechanic=ResourceMechanic.SACRED))
    digger = await make_entity(session, "Diggers", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    faithful = await make_entity(session, "Faithful", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    await bond(session, digger.id, resource.id, BondKind.OWNS)
    await bond(session, faithful.id, resource.id, BondKind.OWNS)
    await bond(session, faithful.id, son.id, BondKind.WORSHIPS)
    await session.flush()
    tuned = economy(rules, sacred_resource_curse_chance=100)
    await resource_mechanics(make_context(session, tuned, 3, "resource_mechanics"))
    entities = EntityRepository(session)
    assert son.wrath == 20 + tuned.economy.sacred_wrath
    assert await entities.has_flag(digger.id, EntityFlag.CURSED)
    assert not await entities.has_flag(faithful.id, EntityFlag.CURSED)
    assert await BondRepository(session).exists_between(son.id, digger.id, BondKind.CURSED)
    assert god_lines.ECONOMY_SACRED_CURSE.key in await chronicle_keys(session)


async def test_a_market_moves_along_an_open_route_and_leaves_its_old_trade(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    second = await add_world(session, "Kesh")
    far_region = await make_entity(session, "Kesh Vale", EntityType.REGION, world_id=second.id)
    session.add(RouteRow(world_a_id=world.world.id, world_b_id=second.id, method=TravelMethod.LIGHT_SAIL, duration_epochs=1, danger=0, created_epoch=1))
    folk = await make_entity(session, "Hearthfolk", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    await session.flush()
    ctx = make_context(session, rules, 3, "cosmic_economy")
    market = await found_faction(ctx, EngineKind.WANDERING_MARKET, world.region)
    await bond(session, market.id, folk.id, BondKind.TRADES_WITH)
    tuned = economy(rules, market_found_chance=0, market_move_chance=100, market_trade_chance=0, cosmic_deposit_chance=0, pirate_chance=0)
    await cosmic_economy(make_context(session, tuned, 3, "cosmic_economy"))
    assert market.world_id == second.id and market.location_id == far_region.id
    assert not await BondRepository(session).exists_between(market.id, folk.id, BondKind.TRADES_WITH)
    assert await BondRepository(session).exists_between(market.id, far_region.id, BondKind.INSIDE)
    assert god_lines.ECONOMY_MARKET_MOVED.key in await chronicle_keys(session)


async def test_a_market_lifts_prosperity_and_opens_trade(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    folk = await make_entity(
        session, "Hearthfolk", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id, stats=PeopleStats(population=900, prosperity=40)
    )
    second = await add_world(session, "Kesh")
    session.add(RouteRow(world_a_id=world.world.id, world_b_id=second.id, method=TravelMethod.LIGHT_SAIL, duration_epochs=1, danger=0, created_epoch=1))
    await session.flush()
    market = await found_faction(make_context(session, rules, 3, "cosmic_economy"), EngineKind.WANDERING_MARKET, world.region)
    tuned = economy(rules, market_found_chance=0, market_move_chance=0, market_trade_chance=100, cosmic_deposit_chance=0, pirate_chance=0)
    await cosmic_economy(make_context(session, tuned, 3, "cosmic_economy"))
    assert folk.stats.model_dump()["prosperity"] > 40
    assert await BondRepository(session).exists_between(market.id, folk.id, BondKind.TRADES_WITH)
    markets = list(await session.scalars(select(EntityRow).where(EntityRow.engine_kind == EngineKind.WANDERING_MARKET)))
    assert markets == [market]
