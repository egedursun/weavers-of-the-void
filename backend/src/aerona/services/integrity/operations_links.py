from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyUnitRow
from aerona.db.tables.operations import (
    AdmiraltyRow,
    DepotRow,
    EchelonRow,
    ExpeditionMemberRow,
    ExpeditionRow,
    TheatreRow,
    TransportAssetRow,
)
from aerona.db.tables.warfare import ArmyRow, WarRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.operations import ExpeditionStatus
from aerona.domain.enums.war import WarStatus

UNDER_WAY = (ExpeditionStatus.UNDERWAY, ExpeditionStatus.CAMPED)


async def mend_operations_links(session: AsyncSession) -> int:
    vanished = select(EntityRow.id).where(EntityRow.status != EntityStatus.CANON)
    disbanded = select(ArmyRow.entity_id).where(ArmyRow.disbanded_epoch.is_not(None))
    ended = select(WarRow.id).where(WarRow.status != WarStatus.ONGOING)
    foreign = (
        select(ArmyUnitRow.id)
        .join(EchelonRow, EchelonRow.id == ArmyUnitRow.echelon_id)
        .where(EchelonRow.army_entity_id.is_not(None), EchelonRow.army_entity_id != ArmyUnitRow.army_entity_id)
    )
    alive = select(ExpeditionMemberRow.expedition_id).where(ExpeditionMemberRow.fallen.is_(False))
    statements = [
        delete(EchelonRow).where(EchelonRow.army_entity_id.in_(disbanded)),
        delete(EchelonRow).where(EchelonRow.owner_entity_id.in_(vanished)),
        update(EchelonRow).where(EchelonRow.commander_entity_id.in_(vanished)).values(commander_entity_id=None),
        update(ArmyUnitRow).where(ArmyUnitRow.id.in_(foreign)).values(echelon_id=None),
        delete(DepotRow).where(DepotRow.owner_entity_id.in_(vanished)),
        delete(TransportAssetRow).where(TransportAssetRow.owner_entity_id.in_(vanished)),
        delete(TheatreRow).where(TheatreRow.war_id.in_(ended)),
        update(TheatreRow).where(TheatreRow.marshal_entity_id.in_(vanished)).values(marshal_entity_id=None),
        update(AdmiraltyRow).where(AdmiraltyRow.admiral_entity_id.in_(vanished)).values(admiral_entity_id=None),
        update(ExpeditionMemberRow).where(ExpeditionMemberRow.mortal_entity_id.in_(vanished), ExpeditionMemberRow.fallen.is_(False)).values(fallen=True),
        update(ExpeditionRow).where(ExpeditionRow.status.in_(UNDER_WAY), ExpeditionRow.id.not_in(alive)).values(status=ExpeditionStatus.LOST),
    ]
    mended = 0
    for statement in statements:
        found = await session.execute(statement)
        mended += int(getattr(found, "rowcount", 0) or 0)
    await session.flush()
    return mended
