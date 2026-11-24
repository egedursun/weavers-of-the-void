from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.geology import RegionGeologyRow, RegionStratumRow
from aerona.domain.enums.geology import UndergroundStratum
from aerona.engine.environment.geology import lay_columns
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import seed_core_world, surveyed


async def test_a_survey_keeps_a_cell_already_made_beneath_a_region_and_adds_no_twin(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    await surveyed(session, world)
    region = world.regions[0]
    await session.execute(delete(RegionGeologyRow).where(RegionGeologyRow.region_entity_id == region.id))
    await session.execute(delete(RegionStratumRow).where(RegionStratumRow.region_entity_id == region.id))
    for stratum in UndergroundStratum:
        session.add(RegionStratumRow(region_entity_id=region.id, stratum=stratum, volume=0, pressure=0, locked=[]))
    await session.flush()
    await lay_columns(await manual_context(session, "survey"))
    counts = list(
        await session.execute(
            select(RegionStratumRow.stratum, func.count()).where(RegionStratumRow.region_entity_id == region.id).group_by(RegionStratumRow.stratum)
        )
    )
    assert len(counts) == len(UndergroundStratum) and all(count == 1 for _, count in counts)
    assert await session.scalar(select(func.count()).select_from(RegionGeologyRow).where(RegionGeologyRow.region_entity_id == region.id))
