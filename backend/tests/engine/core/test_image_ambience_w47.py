from dataclasses import fields

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.image_prompter import ambience
from aerona.catalog.worlds import WorldTypeSpec
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.world import WorldType
from tests.engine.core.factories import CoreWorld
from tests.engine.core.test_evolution_w17 import surveyed


def test_a_world_type_carries_no_fixed_list_of_scenery() -> None:
    assert not [field.name for field in fields(WorldTypeSpec) if field.type == "tuple[str, ...]"]


async def test_a_world_s_image_ambience_comes_from_its_own_lands(session: AsyncSession, world: CoreWorld) -> None:
    world.world.world_type = WorldType.SAND
    region = world.regions[0]
    await surveyed(session)
    for row in await session.scalars(select(RegionEnvironmentRow).where(RegionEnvironmentRow.world_id == world.world.id)):
        row.biome_mix = [0, 0, 0, 70, 0, 0] if row.entity_id == region.id else []
    await session.flush()
    found = await ambience(session, world.world)
    assert found is not None
    assert found.biomes and found.biomes[0] == "dry lowland"
