from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.collective import (
    ArmsRow,
    DatingSystemRow,
    MobRow,
    MovementRow,
    RoleNormRow,
    SocialNormRow,
    StoryletRunRow,
)
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.collective import MobEnd, MobStatus, StoryletStatus
from aerona.domain.enums.entity import EntityStatus


async def mend_collective_links(session: AsyncSession, epoch: int) -> int:
    vanished = select(EntityRow.id).where(EntityRow.status != EntityStatus.CANON)
    statements = [
        update(MobRow)
        .where(MobRow.status != MobStatus.DISPERSED, MobRow.settlement_entity_id.in_(vanished))
        .values(status=MobStatus.DISPERSED, ended_by=MobEnd.FATIGUE),
        update(MovementRow).where(MovementRow.ended_epoch.is_(None), MovementRow.settlement_entity_id.in_(vanished)).values(ended_epoch=epoch),
        update(StoryletRunRow)
        .where(StoryletRunRow.status == StoryletStatus.OPEN, StoryletRunRow.chooser_node_id.in_(vanished))
        .values(status=StoryletStatus.EXPIRED, resolved_epoch=epoch),
        delete(SocialNormRow).where(SocialNormRow.holder_entity_id.in_(vanished)),
        delete(RoleNormRow).where(RoleNormRow.holder_entity_id.in_(vanished)),
        delete(DatingSystemRow).where(DatingSystemRow.holder_entity_id.in_(vanished)),
        update(ArmsRow)
        .where(ArmsRow.quartered_entity_id.is_not(None), ArmsRow.quartered_entity_id.not_in(select(ArmsRow.holder_entity_id)))
        .values(quartered_entity_id=None),
        update(VesselProfileRow).where(VesselProfileRow.design_id.is_not(None), VesselProfileRow.entity_id.in_(vanished)).values(design_id=None),
    ]
    mended = 0
    for statement in statements:
        found = await session.execute(statement)
        mended += int(getattr(found, "rowcount", 0) or 0)
    await session.flush()
    return mended
