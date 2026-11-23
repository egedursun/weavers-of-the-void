from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.happenings import RiverShiftRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.polity import PolityTerritoryRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import RiverClass, ScarKind
from aerona.domain.enums.happening import RiverShiftCause
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.structure import StructureKind
from aerona.domain.models.entity_stats import PolityStats, StructureStats
from aerona.engine.context import TickContext
from aerona.engine.environment.geomorph import erupted
from aerona.engine.primitives.manual import manual_context
from aerona.engine.water.courses import burst_slide_dams, silt_out, slide_dam, works_move
from tests.engine.core.factories import CoreWorld, entity, seed_core_world, surveyed, tuned_rules

CERTAIN = tuned_rules(rivers={"silting_shift_pct": 100, "works_shift_pct": 100, "eruption_shift_pct": 100, "slide_dam_pct": 100, "slide_dam_burst_pct": 100})


async def river_world(session: AsyncSession) -> tuple[CoreWorld, dict[int, RegionEnvironmentRow], TickContext]:
    world = await seed_core_world(session)
    await surveyed(session, world)
    lands = {row.entity_id: row for row in await session.scalars(select(RegionEnvironmentRow).where(RegionEnvironmentRow.world_id == world.world.id))}
    lands[world.regions[0].id].river_class = RiverClass.RIVER
    await session.flush()
    return world, lands, await manual_context(session, "test", CERTAIN)


async def causes(session: AsyncSession) -> set[RiverShiftCause]:
    return set(await session.scalars(select(RiverShiftRow.cause)))


async def test_heavy_silt_turns_a_river_and_light_silt_does_not(session: AsyncSession) -> None:
    world, lands, ctx = await river_world(session)
    source = world.regions[0].id
    assert await silt_out(ctx, lands, {source: CERTAIN.rivers.silting_shift_load - 1}) == 0
    assert await silt_out(ctx, lands, {source: CERTAIN.rivers.silting_shift_load}) == 1
    assert RiverShiftCause.SILTING in await causes(session) and lands[source].river_class is RiverClass.STREAM


async def test_new_works_turn_a_river_and_the_land_downstream_bears_a_grudge(session: AsyncSession) -> None:
    world, lands, ctx = await river_world(session)
    source = world.regions[0].id
    canal = await entity(session, "The Cut", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=source)
    session.add(StructureProfileRow(structure_entity_id=canal.id, kind=StructureKind.CANAL, built_epoch=ctx.epoch))
    upper = await entity(session, "Upper Realm", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    lower = await entity(session, "Lower Realm", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(PolityTerritoryRow(polity_entity_id=upper.id, region_entity_id=source, control=80, locked=[]))
    for region in world.regions[1:]:
        session.add(PolityTerritoryRow(polity_entity_id=lower.id, region_entity_id=region.id, control=80, locked=[]))
    await session.flush()
    assert await works_move(ctx, lands) == 1
    assert RiverShiftCause.WORKS in await causes(session)
    grudge = await session.scalar(select(MemoryRow).where(MemoryRow.holder_node_id == lower.id, MemoryRow.kind == MemoryKind.HARMED_ME))
    assert grudge is not None and grudge.subject_node_id == upper.id


async def test_an_eruption_can_turn_its_river(session: AsyncSession) -> None:
    world, lands, ctx = await river_world(session)
    shape = await erupted(ctx, world.regions[0], 60)
    assert shape is not None and shape.last_eruption_epoch == ctx.epoch
    assert RiverShiftCause.ERUPTION in await causes(session)
    assert lands[world.regions[0].id].scars.get(ScarKind.BURNED.value, 0) > 0


async def test_a_landslide_dams_a_river_and_the_dam_bursts_the_next_epoch(session: AsyncSession) -> None:
    world, lands, ctx = await river_world(session)
    assert await slide_dam(ctx, lands[world.regions[0].id])
    shift = await session.scalar(select(RiverShiftRow).where(RiverShiftRow.cause == RiverShiftCause.LANDSLIDE))
    assert shift is not None
    world.cosmos.epoch += 1
    await session.flush()
    later = await manual_context(session, "test", CERTAIN)
    assert later.epoch == ctx.epoch + 1
    assert await burst_slide_dams(later, lands) == 1
    kinds = set(await session.scalars(select(IncidentRow.kind)))
    assert {"river.dammed_by_slide", "river.dam_burst"} <= kinds
    assert lands[shift.to_region_id].scars.get(ScarKind.FLOODED.value, 0) >= CERTAIN.rivers.burst_flood
