from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.celestial import StarRow
from aerona.db.tables.economy import ResourceProfileRow, WorldMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.economy import MaterialOrigin
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.world import StarType
from aerona.domain.models.entity_stats import PlaceStats
from aerona.engine.phases.production import world_materials
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, entity, tuned_rules

CERTAIN = tuned_rules(materials={"world_material_god_chance": 100, "world_material_star_chance": 100})


async def godflesh_at(session: AsyncSession, place_id: int) -> list[int]:
    statement = (
        select(ResourceProfileRow.resource_entity_id)
        .join(EntityRow, EntityRow.id == ResourceProfileRow.resource_entity_id)
        .where(EntityRow.location_id == place_id, ResourceProfileRow.material == MaterialKind.GODFLESH)
    )
    return list(await session.scalars(statement))


async def test_a_dead_gods_remains_open_one_godflesh_seam_and_a_substance_of_their_own(session: AsyncSession, world: CoreWorld) -> None:
    corpse = await entity(session, "Fallen Height", EntityType.PLACE, PlaceStats(), world_id=world.world.id, location_id=world.regions[0].id)
    corpse.engine_kind = EngineKind.DEAD_GOD
    await session.flush()
    await world_materials(await manual_context(session, "materials", rules=CERTAIN))
    assert len(await godflesh_at(session, corpse.id)) == 1
    origins = list(await session.scalars(select(WorldMaterialRow.origin).where(WorldMaterialRow.world_id == world.world.id)))
    assert MaterialOrigin.DEAD_GOD in origins
    await world_materials(await manual_context(session, "materials", rules=CERTAIN))
    assert len(await godflesh_at(session, corpse.id)) == 1


async def test_a_plain_place_yields_no_godflesh(session: AsyncSession, world: CoreWorld) -> None:
    place = await entity(session, "Quiet Hill", EntityType.PLACE, PlaceStats(), world_id=world.world.id, location_id=world.regions[0].id)
    await world_materials(await manual_context(session, "materials", rules=CERTAIN))
    assert await godflesh_at(session, place.id) == []


async def test_a_dead_star_lets_its_core_fall_on_a_region_of_its_world(session: AsyncSession, world: CoreWorld) -> None:
    star = await session.get(StarRow, world.world.star_id)
    assert star is not None
    star.star_type = StarType.DEAD_STAR
    await session.flush()
    await world_materials(await manual_context(session, "materials", rules=CERTAIN))
    fallen = await session.scalar(select(WorldMaterialRow).where(WorldMaterialRow.origin == MaterialOrigin.STAR))
    assert fallen is not None and fallen.world_id == world.world.id


async def test_a_living_star_drops_nothing(session: AsyncSession, world: CoreWorld) -> None:
    await world_materials(await manual_context(session, "materials", rules=CERTAIN))
    assert await session.scalar(select(WorldMaterialRow).where(WorldMaterialRow.origin == MaterialOrigin.STAR)) is None
