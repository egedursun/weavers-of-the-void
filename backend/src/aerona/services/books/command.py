from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.command import AREAS
from aerona.db.tables.warfare import ArmyRow
from aerona.engine.military.command import best_area, command_areas
from aerona.services.books.typed import TypedFact, TypedIndex, TypedSection


async def add_command_areas(session: AsyncSession, index: TypedIndex) -> int:
    commanders = sorted(
        {commander for commander in await session.scalars(select(ArmyRow.commander_entity_id).where(ArmyRow.commander_entity_id.is_not(None))) if commander}
    )
    for commander_id in commanders:
        areas = await command_areas(session, commander_id)
        best = best_area(areas)
        facts = [TypedFact(AREAS[area].label, f"{value} ({AREAS[area].effect})") for area, value in areas.items()]
        if best is not None:
            facts.insert(0, TypedFact("Leads best at", AREAS[best].label))
        index.sections[commander_id].append(TypedSection("Command areas", facts=facts))
    return len(commanders)
