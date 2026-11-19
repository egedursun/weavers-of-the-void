from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.fossils import FossilBedRow
from aerona.domain.enums.fossil import FossilSource, Preservation
from aerona.engine.context import TickContext
from aerona.engine.ecology.fossils import depth_of, preservation_of
from tests.engine.core.factories import CoreWorld, surveyed


async def test_a_wet_land_keeps_its_beds_in_bog_and_a_dry_one_keeps_them_dry(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    await surveyed(session, world)
    land = await session.get(RegionEnvironmentRow, world.regions[0].id)
    assert land is not None
    land.wetland = ctx.rules.fossils.bog_wetland
    assert await preservation_of(ctx, land.entity_id, frozen=False) is Preservation.BOG
    assert await preservation_of(ctx, land.entity_id, frozen=True) is Preservation.ICE
    land.wetland, land.rainfall = 0, 0
    assert await preservation_of(ctx, land.entity_id, frozen=False) is Preservation.DRY


def test_a_bed_lies_deeper_with_the_years(ctx: TickContext) -> None:
    bed = FossilBedRow(region_entity_id=1, source=FossilSource.MEGAFAUNA, richness=30, laid_epoch=0, layer=0, locked=[])
    assert depth_of(ctx, bed) == min(100, ctx.epoch * ctx.rules.fossils.layer_per_epoch)
