from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.vehicles import DesignSectionRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.vehicles import VehicleFrame, VehicleSection
from aerona.domain.models.entity_stats import PeopleStats
from aerona.engine.collective.designs import draw_design
from aerona.engine.primitives.manual import manual_context
from aerona.engine.vehicles.fixups import reseat_sections
from tests.engine.core.factories import CoreWorld, entity


async def test_old_sections_of_a_motorboat_and_a_sledge_are_reseated(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "reseat")
    folk = await entity(session, "Ardan", EntityType.PEOPLE, PeopleStats(population=4000), world_id=world.world.id)
    boat = await draw_design(ctx, folk, VehicleFrame.MOTORBOAT)
    sledge = await draw_design(ctx, folk, VehicleFrame.SLEDGE)
    engine = await session.get(DesignSectionRow, (boat.id, VehicleSection.ENGINE))
    assert engine is not None
    await session.delete(engine)
    session.add(DesignSectionRow(design_id=boat.id, section=VehicleSection.OARS, function=engine.function, neighbours=["hull"]))
    session.add(DesignSectionRow(design_id=sledge.id, section=VehicleSection.WHEELS, function=engine.function, neighbours=[]))
    await session.flush()
    assert await reseat_sections(ctx) >= 2
    sections = {(row.design_id, row.section) for row in await session.scalars(select(DesignSectionRow))}
    assert (boat.id, VehicleSection.ENGINE) in sections and (boat.id, VehicleSection.OARS) not in sections
    assert (sledge.id, VehicleSection.WHEELS) not in sections
