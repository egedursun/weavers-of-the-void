from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.disease import DiseaseCureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.evolution import CarrierRow, CureResearchRow, PlagueResponseRow, SpeciesTraitRow
from aerona.domain.enums.disease import CureSource
from aerona.domain.enums.entity import EntityStatus


async def mend_evolution_links(session: AsyncSession, epoch: int) -> int:
    vanished = select(EntityRow.id).where(EntityRow.status != EntityStatus.CANON)
    gone = select(EntityRow.id).where(EntityRow.status.not_in([EntityStatus.CANON, EntityStatus.DEAD]))
    mended = 0
    statements = [
        delete(CarrierRow).where(CarrierRow.mortal_entity_id.in_(vanished)),
        delete(PlagueResponseRow).where(PlagueResponseRow.community_entity_id.in_(vanished)),
        delete(CureResearchRow).where(CureResearchRow.institution_entity_id.in_(vanished), CureResearchRow.cured_epoch.is_(None)),
        delete(SpeciesTraitRow).where(SpeciesTraitRow.species_entity_id.in_(gone)),
    ]
    for statement in statements:
        found = await session.execute(statement)
        mended += int(getattr(found, "rowcount", 0) or 0)
    for research in await session.scalars(select(CureResearchRow).where(CureResearchRow.cured_epoch.is_not(None))):
        seat = await session.get(EntityRow, research.institution_entity_id)
        holder = seat.location_id if seat is not None else None
        if holder is None or await session.get(DiseaseCureRow, (research.disease_entity_id, holder)) is not None:
            continue
        session.add(
            DiseaseCureRow(
                disease_entity_id=research.disease_entity_id, community_entity_id=holder, source=CureSource.KNOWLEDGE, since_epoch=research.cured_epoch or epoch
            )
        )
        mended += 1
    await session.flush()
    return mended
