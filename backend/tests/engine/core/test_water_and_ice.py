from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.fossils import FossilBedRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.water import CoastRow, RegionCryosphereRow
from aerona.db.write_guard import HELD_SCOPE, HeldScope
from aerona.domain.enums.economy import TradeMode
from aerona.domain.enums.fossil import FossilSource
from aerona.domain.enums.water import CoastForm
from aerona.engine.context import TickContext
from aerona.engine.water.ice import WaterTally, ice_open_pct, keep_water
from tests.engine.core.factories import CoreWorld, surveyed


async def land_of(session: AsyncSession, world: CoreWorld) -> RegionEnvironmentRow:
    await surveyed(session, world)
    land = await session.get(RegionEnvironmentRow, world.regions[0].id)
    assert land is not None
    return land


async def test_a_cold_land_freezes_closes_its_waters_and_shortens_its_sea_roads(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    land = await land_of(session, world)
    land.temperature = 2
    await session.flush()
    await keep_water(ctx, WaterTally())
    ice = await session.get(RegionCryosphereRow, land.entity_id)
    assert ice is not None and ice.ice_months >= ctx.rules.water_and_ice.ice_route_block_months and ice.frozen_depth > 0
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "land.ice_closed")) is not None
    assert await ice_open_pct(ctx, TradeMode.SEA, [land.entity_id]) < 100
    assert await ice_open_pct(ctx, TradeMode.ROAD, [land.entity_id]) == 100


async def test_a_thaw_gives_up_a_frozen_bed(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    land = await land_of(session, world)
    session.add(RegionCryosphereRow(region_entity_id=land.entity_id, frozen_depth=90, locked=[]))
    session.add(FossilBedRow(region_entity_id=land.entity_id, world_id=world.world.id, source=FossilSource.MEGAFAUNA, richness=40, frozen=True, locked=[]))
    land.temperature = 60
    await session.flush()
    await keep_water(ctx, WaterTally())
    bed = await session.scalar(select(FossilBedRow).where(FossilBedRow.region_entity_id == land.entity_id))
    assert bed is not None and bed.found_epoch == ctx.epoch
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "land.thaw_release")) is not None


async def test_a_harbour_full_of_sediment_silts_up(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    land = await land_of(session, world)
    session.add(CoastRow(region_entity_id=land.entity_id, form=CoastForm.LAGOON, harbour_silting=100, locked=[]))
    await session.flush()
    await keep_water(ctx, WaterTally())
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "land.silted")) is not None


async def test_a_held_land_keeps_its_ice(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    land = await land_of(session, world)
    land.temperature = 2
    await session.flush()
    token = HELD_SCOPE.set(HeldScope(None, frozenset({land.entity_id})))
    try:
        await keep_water(ctx, WaterTally())
    finally:
        HELD_SCOPE.reset(token)
    assert await session.get(RegionCryosphereRow, land.entity_id) is None
