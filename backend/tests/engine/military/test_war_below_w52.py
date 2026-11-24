from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.geology import RegionStratumRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.military import CampaignFrontRow
from aerona.domain.enums.economy import TradeMode
from aerona.domain.enums.geology import DeepPassageOrigin, DeepPassageState, UndergroundStratum
from aerona.domain.enums.military import SiegeAction, UnitKind
from aerona.engine.context import TickContext
from aerona.engine.environment.cells import make_passage, passage_between
from aerona.engine.environment.deep_war import press_below
from aerona.engine.military.logistics import March, mark_front
from aerona.engine.primitives.deep_paths import cut_below, route_cells, tell_route_cut
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.services.war import open_war
from tests.engine.core.factories import CoreWorld, settlement, surveyed
from tests.engine.military.w52_war_setup import army_of

U = UndergroundStratum


async def two_cells(session: AsyncSession, world: CoreWorld) -> tuple[EntityRow, EntityRow]:
    await surveyed(session, world)
    first, second = world.regions[0], world.regions[1]
    for region in (first, second):
        session.add(RegionStratumRow(region_entity_id=region.id, stratum=U.CAVERN_UPPER, volume=0, pressure=0, locked=[]))
    await session.flush()
    return first, second


async def test_a_route_below_runs_along_its_passages_and_a_collapse_cuts_it(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    first, second = await two_cells(session, world)
    assert second.id in (await RegionAtlas.load(session)).neighbours(first.id)
    west = await settlement(session, "Westdeep", world, first)
    east = await settlement(session, "Eastdeep", world, second)
    west.stratum = east.stratum = U.CAVERN_UPPER
    await session.flush()
    way = await make_passage(ctx, world.world.id, (first.id, U.CAVERN_UPPER), (second.id, U.CAVERN_UPPER), origin=DeepPassageOrigin.NATURAL)
    cells = route_cells(await RegionAtlas.load(session), west, east)
    assert cells == [(first.id, U.CAVERN_UPPER), (second.id, U.CAVERN_UPPER)]
    assert not await cut_below(ctx, west.id, TradeMode.UNDERGROUND, cells)
    way.state = DeepPassageState.COLLAPSED
    await session.flush()
    assert await cut_below(ctx, west.id, TradeMode.UNDERGROUND, cells)
    assert not await cut_below(ctx, west.id, TradeMode.ROAD, cells)
    await tell_route_cut(ctx, west.id, cells)
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "route.passage_cut")) is not None


async def test_a_siege_below_collapses_the_ways_into_the_town_but_keeps_the_besiegers_own(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    first, second = await two_cells(session, world)
    assert second.id in (await RegionAtlas.load(session)).neighbours(first.id)
    town = await settlement(session, "Underkeep", world, first)
    town.stratum = U.CAVERN_UPPER
    await session.flush()
    opening = await make_passage(ctx, world.world.id, (first.id, None), (first.id, U.CAVERN_UPPER), origin=DeepPassageOrigin.NATURAL)
    level = await make_passage(ctx, world.world.id, (first.id, U.CAVERN_UPPER), (second.id, U.CAVERN_UPPER), origin=DeepPassageOrigin.NATURAL)
    army_id, profile = await army_of(ctx, world.people.id, world.world.id)
    profile.region_entity_id, profile.stratum = second.id, U.CAVERN_UPPER
    army = await session.get(EntityRow, army_id)
    assert army is not None
    march = March(army, world.people, profile, town.id, True)
    await press_below(ctx, town, march, SiegeAction.BLOCKADE, await RegionAtlas.load(session))
    assert opening.state is DeepPassageState.COLLAPSED and level.state is DeepPassageState.OPEN


async def test_mining_a_siege_below_digs_a_passage_under_the_town(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    first, _ = await two_cells(session, world)
    town = await settlement(session, "Deepfort", world, first)
    town.stratum = U.CAVERN_UPPER
    await session.flush()
    army_id, profile = await army_of(ctx, world.people.id, world.world.id)
    profile.region_entity_id = first.id
    army = await session.get(EntityRow, army_id)
    assert army is not None
    await press_below(ctx, town, March(army, world.people, profile, town.id, True), SiegeAction.MINE, await RegionAtlas.load(session))
    dug = await passage_between(ctx, (first.id, None), (first.id, U.CAVERN_UPPER))
    assert dug is not None and dug.state is DeepPassageState.DIGGING


async def test_a_front_is_kept_per_cell(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    first, second = await two_cells(session, world)
    kinds = list(UnitKind)[:4]
    _, high = await army_of(ctx, world.people.id, world.world.id, kind=kinds[0])
    _, low = await army_of(ctx, world.people.id, world.world.id, kind=kinds[1])
    high.region_entity_id = low.region_entity_id = first.id
    low.stratum = U.CAVERN_UPPER
    above = await army_of(ctx, world.people.id, world.world.id, kind=kinds[2])
    below = await army_of(ctx, world.people.id, world.world.id, kind=kinds[3])
    above[1].region_entity_id, below[1].region_entity_id, below[1].stratum = second.id, second.id, U.CAVERN_UPPER
    foe = await settlement(session, "Foehold", world, second)
    war = await open_war(ctx, world.people, foe)
    await session.flush()
    await mark_front(ctx, war.id, high, above[1])
    await mark_front(ctx, war.id, low, below[1])
    fronts = list(await session.scalars(select(CampaignFrontRow).order_by(CampaignFrontRow.id)))
    assert len(fronts) == 2 and {(row.first_stratum, row.second_stratum) for row in fronts} == {(None, None), (U.CAVERN_UPPER, U.CAVERN_UPPER)}
