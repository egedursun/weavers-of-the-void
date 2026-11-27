from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.collective import GenerationRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.collective.book import population_of
from aerona.engine.collective.generations import fit_to_people, living_generations


async def generations_beyond_people(session: AsyncSession) -> list[int]:
    towns = select(GenerationRow.community_entity_id).where(GenerationRow.passed_epoch.is_(None), GenerationRow.alive > 0).distinct()
    found: list[int] = []
    for town in await session.scalars(select(EntityRow).where(EntityRow.id.in_(towns), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)):
        if held(town.id):
            continue
        unheld = [row for row in await living_generations(session, town.id) if "alive" not in (row.locked or [])]
        if unheld and sum(row.alive for row in unheld) > population_of(town):
            found.append(town.id)
    return found


async def fit_generations(session: AsyncSession, town_id: int) -> None:
    town = await session.get(EntityRow, town_id)
    if town is not None:
        await fit_to_people(session, town)
