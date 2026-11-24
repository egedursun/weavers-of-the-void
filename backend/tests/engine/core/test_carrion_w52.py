from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.couplings import CARRION_RESTS, KEEPING_RESTS
from aerona.db.tables.couplings import CarrionPulseRow
from aerona.db.tables.fossils import FossilBedRow
from aerona.domain.enums.couplings import CarrionRest
from aerona.domain.enums.environment import TerrainKind
from aerona.domain.enums.fossil import FossilSource
from aerona.engine.couplings.carrion import lay_remains, rest_of, settle_rest
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, tuned_rules
from tests.engine.core.living_kinds import land, told

RULES = Rules()


def test_eight_rests_each_with_every_pressure_and_keeping_read_from_the_catalogue() -> None:
    assert set(CARRION_RESTS) == set(CarrionRest) and len(CarrionRest) == 9
    assert {rest for rest, spec in CARRION_RESTS.items() if spec.keeps} == KEEPING_RESTS
    assert CARRION_RESTS[CarrionRest.BURNED].gone and CARRION_RESTS[CarrionRest.BURNED].scavenger(RULES) == 0
    assert CARRION_RESTS[CarrionRest.SUNK].scavenger(RULES) > 0 and not CARRION_RESTS[CarrionRest.BURIED].gone
    assert CARRION_RESTS[CarrionRest.BURIED].disease(RULES) < CARRION_RESTS[CarrionRest.ROTTING].disease(RULES)


async def test_the_dead_of_a_watery_land_sink_and_a_change_of_rest_is_told(session: AsyncSession, world: CoreWorld) -> None:
    region = world.regions[0]
    ground = await land(session, world, region, dominant_terrain=TerrainKind.MARSH, burned_epoch=None)
    ctx = await manual_context(session, "carrion")
    assert await rest_of(ctx, region, ground) is CarrionRest.SUNK
    row = CarrionPulseRow(region_entity_id=region.id, carrion=40, rest=CarrionRest.ROTTING, locked=[])
    session.add(row)
    await settle_rest(ctx, row, region, ground, CarrionRest.BURIED)
    assert row.rest is CarrionRest.BURIED and await told(session, "carrion.laid")
    held_row = CarrionPulseRow(region_entity_id=world.regions[1].id, carrion=10, rest=CarrionRest.ROTTING, locked=["rest"])
    await settle_rest(ctx, held_row, world.regions[1], None, CarrionRest.BURNED)
    assert held_row.rest is CarrionRest.ROTTING


async def test_a_change_of_rest_with_no_dead_left_is_not_told(session: AsyncSession, world: CoreWorld) -> None:
    region = world.regions[0]
    ctx = await manual_context(session, "carrion")
    row = CarrionPulseRow(region_entity_id=region.id, carrion=0, rest=CarrionRest.ROTTING, locked=[])
    session.add(row)
    await settle_rest(ctx, row, region, None, CarrionRest.BURIED)
    assert row.rest is CarrionRest.BURIED and not await told(session, "carrion.laid")


async def test_buried_dead_lay_one_bed_of_remains(session: AsyncSession, world: CoreWorld) -> None:
    region = world.regions[0]
    ctx = await manual_context(session, "carrion", tuned_rules(carrion={"buried_fossil": 100}))
    row = CarrionPulseRow(region_entity_id=region.id, carrion=40, rest=CarrionRest.BURIED, locked=[])
    await lay_remains(ctx, row, region)
    await session.flush()
    await lay_remains(ctx, row, region)
    await session.flush()
    beds = await session.scalar(
        select(func.count()).select_from(FossilBedRow).where(FossilBedRow.region_entity_id == region.id, FossilBedRow.source == FossilSource.BURIED_DEAD)
    )
    assert beds == 1
