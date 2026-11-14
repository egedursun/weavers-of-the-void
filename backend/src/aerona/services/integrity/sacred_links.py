from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sacred import MillenarianRow, MysticRow, PetitionRow, SpiritOfficeRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.sacred import MillenarianStage, MysticState, PetitionStatus

OPEN = (PetitionStatus.FILED, PetitionStatus.DELAYED, PetitionStatus.APPEALED)
LIVING = (MillenarianStage.STIRRING, MillenarianStage.GATHERING, MillenarianStage.VIGIL, MillenarianStage.MARCHING, MillenarianStage.REDATED)


async def mend_sacred_links(session: AsyncSession) -> int:
    vanished = select(EntityRow.id).where(EntityRow.status != EntityStatus.CANON)
    offices = select(SpiritOfficeRow.spirit_entity_id).where(SpiritOfficeRow.dismissed.is_(False))
    mended = 0
    for statement in (
        update(SpiritOfficeRow).where(SpiritOfficeRow.spirit_entity_id.in_(vanished), SpiritOfficeRow.dismissed.is_(False)).values(dismissed=True),
        update(SpiritOfficeRow).where(SpiritOfficeRow.superior_spirit_id == SpiritOfficeRow.spirit_entity_id).values(superior_spirit_id=None),
        update(SpiritOfficeRow)
        .where(SpiritOfficeRow.superior_spirit_id.is_not(None), SpiritOfficeRow.superior_spirit_id.not_in(offices))
        .values(superior_spirit_id=None),
        update(PetitionRow).where(PetitionRow.status.in_(OPEN), PetitionRow.office_spirit_id.not_in(offices)).values(status=PetitionStatus.DISMISSED),
        update(MysticRow).where(MysticRow.mortal_entity_id.in_(vanished), MysticRow.state != MysticState.LAPSED).values(state=MysticState.LAPSED),
        update(MillenarianRow)
        .where(MillenarianRow.settlement_entity_id.in_(vanished), MillenarianRow.stage.in_(LIVING))
        .values(stage=MillenarianStage.DISPERSED),
    ):
        result = await session.execute(statement)
        mended += max(0, getattr(result, "rowcount", 0) or 0)
    return mended
