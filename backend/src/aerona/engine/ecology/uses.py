from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.ecology import SpeciesUseRow
from aerona.domain.enums.ecology import AnimalRole


def pending_use(session: AsyncSession, species_id: int, use: AnimalRole) -> SpeciesUseRow | None:
    return next((row for row in session.new if isinstance(row, SpeciesUseRow) and row.species_entity_id == species_id and row.use is use), None)


async def give_use(session: AsyncSession, species_id: int, use: AnimalRole) -> SpeciesUseRow:
    row = pending_use(session, species_id, use) or await session.get(SpeciesUseRow, (species_id, use))
    if row is None:
        row = SpeciesUseRow(species_entity_id=species_id, use=use)
        session.add(row)
    return row
