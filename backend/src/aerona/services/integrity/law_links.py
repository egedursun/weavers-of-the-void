from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.law_depth import LegalSystemRow, OutlawRow, PrisonerRow, PrisonRow, SpyCellRow
from aerona.db.tables.military import SpyAgentRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.structure import StructureKind


async def mend_law_links(session: AsyncSession) -> int:
    vanished = select(EntityRow.id).where(EntityRow.status != EntityStatus.CANON)
    prisons = select(StructureProfileRow.structure_entity_id).where(StructureProfileRow.kind == StructureKind.PRISON)
    cells = select(SpyCellRow.id)
    statements = [
        delete(PrisonerRow).where(PrisonerRow.mortal_entity_id.in_(vanished)),
        delete(PrisonerRow).where(PrisonerRow.prison_entity_id.not_in(prisons)),
        delete(PrisonRow).where(PrisonRow.structure_entity_id.not_in(prisons)),
        delete(OutlawRow).where(OutlawRow.mortal_entity_id.in_(vanished)),
        delete(LegalSystemRow).where(LegalSystemRow.holder_entity_id.in_(vanished)),
        update(SpyAgentRow).where(SpyAgentRow.cell_id.is_not(None), SpyAgentRow.cell_id.not_in(cells)).values(cell_id=None),
    ]
    mended = 0
    for statement in statements:
        found = await session.execute(statement)
        mended += int(getattr(found, "rowcount", 0) or 0)
    await session.flush()
    return mended
