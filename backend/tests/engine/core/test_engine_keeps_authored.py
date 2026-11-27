from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.cartography.model import RegionGeography
from aerona.db.tables.celestial import WorldMapRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.environment import CoastKind, RiverClass
from aerona.engine.environment.control import set_mineral
from aerona.engine.phases.environment import environment_survey
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, region_record

HELD_SEAM = "godstone"


def geography() -> RegionGeography:
    return RegionGeography(
        biome_mix=[40, 30, 30],
        elevation_mean=50,
        roughness=40,
        moisture=50,
        latitude=40,
        forest=30,
        wetland=10,
        river_flow=0.0,
        river_class=RiverClass.NONE,
        coast_kind=CoastKind.NONE,
        land_share=100,
    )


async def test_a_region_surveyed_late_keeps_the_seams_set_on_it_before_its_map(session: AsyncSession, world: CoreWorld) -> None:
    stored = await session.scalar(select(WorldMapRow).where(WorldMapRow.world_id == world.world.id))
    assert stored is not None
    await session.delete(stored)
    await session.flush()
    await environment_survey(await manual_context(session, "survey"))
    region = world.regions[0]
    ground = await session.get(RegionEnvironmentRow, region.id)
    assert ground is not None and not ground.surveyed
    set_mineral(ground, HELD_SEAM, 77, lock=True)
    await session.flush()
    records = []
    for each in world.regions:
        neighbours = [other.id for other in world.regions if other.id != each.id][:1]
        records.append(region_record(each.id, neighbours).model_copy(update={"geography": geography()}).model_dump(mode="json"))
    session.add(WorldMapRow(world_id=world.world.id, generator_version=1, epoch=2, geometry={"regions": records}))
    await session.flush()
    await environment_survey(await manual_context(session, "survey"))
    await session.refresh(ground)
    assert ground.surveyed
    assert ground.mineral_layers.get(HELD_SEAM) == 77
