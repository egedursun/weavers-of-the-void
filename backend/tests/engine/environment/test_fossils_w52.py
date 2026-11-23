from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.economy import CommunityStockRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.fossils import FossilBedRow
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.fossil import FossilReading, FossilSource
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.models.entity_stats import EventStats
from aerona.engine.ecology.fossils import READ_EFFECTS, READINGS, reading_of, remains, told
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import entity, seed_core_world, settlement, surveyed

RULES = Rules()


async def held_stock(session: AsyncSession, holder: int, commodity: CommodityKind, material: MaterialKind | None = None) -> int:
    statement = select(func.sum(CommunityStockRow.quantity)).where(CommunityStockRow.community_entity_id == holder, CommunityStockRow.commodity == commodity)
    if material is not None:
        statement = statement.where(CommunityStockRow.material == material)
    return int(await session.scalar(statement) or 0)


def test_every_reading_is_drawn_from_a_value_and_has_its_effect() -> None:
    assert {reading for _, reading in READINGS} == set(FossilReading) - {FossilReading.UNREAD}
    assert set(READ_EFFECTS) == {reading for _, reading in READINGS}
    assert dict(READINGS)[ValueAxis.WEALTH] is FossilReading.MATERIAL and dict(READINGS)[ValueAxis.MERCY] is FossilReading.MEDICINE


async def test_a_dead_god_leaves_a_bed_that_draws_the_faithful_and_yields_its_tissue(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    await surveyed(session, world)
    ctx = await manual_context(session, "test", RULES)
    region = world.regions[0]
    corpse = await entity(session, "The Fallen One", EntityType.EVENT, EventStats(), world_id=world.world.id, location_id=region.id)
    corpse.engine_kind = EngineKind.DEAD_GOD
    await session.flush()
    assert any(found.entity.id == corpse.id and found.source is FossilSource.GOD for found in await remains(ctx))
    town = await settlement(session, "Bonefield", world, region)
    bed = FossilBedRow(region_entity_id=region.id, world_id=world.world.id, source=FossilSource.GOD, richness=60, reading=FossilReading.MATERIAL, locked=[])
    session.add(bed)
    land = await session.get(RegionEnvironmentRow, region.id)
    assert land is not None
    before = land.sacredness
    await session.flush()
    await told(ctx, bed, town)
    await session.flush()
    assert land.sacredness == before + RULES.fossils.dead_god_draw
    assert await held_stock(session, town.id, CommodityKind.ORE, MaterialKind.DIVINE_TISSUE) > 0


async def test_old_bones_are_ground_into_medicine_or_worked_as_material(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    ctx = await manual_context(session, "test", RULES)
    town = await settlement(session, "Marrow", world, world.regions[0])
    ground_bed = FossilBedRow(region_entity_id=world.regions[0].id, source=FossilSource.MEGAFAUNA, richness=50, reading=FossilReading.MEDICINE, locked=[])
    worked_bed = FossilBedRow(region_entity_id=world.regions[0].id, source=FossilSource.BEAST, richness=50, reading=FossilReading.MATERIAL, locked=[])
    session.add_all([ground_bed, worked_bed])
    await session.flush()
    await told(ctx, ground_bed, town)
    await told(ctx, worked_bed, town)
    await session.flush()
    assert await held_stock(session, town.id, CommodityKind.MEDICINE) == round(50 / 10 * RULES.fossils.medicine_demand)
    assert await held_stock(session, town.id, CommodityKind.ORE, MaterialKind.CALCIFIED_TISSUE) > 0
    assert await reading_of(ctx, town) in set(FossilReading)
