from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.agrarian import (
    BrandRow,
    CentralPlaceRow,
    CommonsRow,
    FamineLoreRow,
    GameReserveRow,
    KeystoneResourceRow,
    LandRingRow,
    PerennialRow,
    PreparednessRow,
    ReconstructionRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus


async def mend_agrarian_links(session: AsyncSession) -> int:
    vanished = select(EntityRow.id).where(EntityRow.status != EntityStatus.CANON)
    statements = [
        delete(CentralPlaceRow).where(CentralPlaceRow.settlement_entity_id.in_(vanished)),
        update(CentralPlaceRow).where(CentralPlaceRow.served_by_entity_id.in_(vanished)).values(served_by_entity_id=None),
        update(LandRingRow).where(LandRingRow.market_entity_id.in_(vanished)).values(market_entity_id=None),
        delete(PreparednessRow).where(PreparednessRow.settlement_entity_id.in_(vanished)),
        delete(ReconstructionRow).where(ReconstructionRow.settlement_entity_id.in_(vanished), ReconstructionRow.finished_epoch.is_(None)),
        update(ReconstructionRow).where(ReconstructionRow.planner_entity_id.in_(vanished)).values(planner_entity_id=None),
        update(PerennialRow).where(PerennialRow.owner_node_id.in_(vanished)).values(owner_node_id=None),
        update(CommonsRow).where(CommonsRow.steward_entity_id.in_(vanished)).values(steward_entity_id=None),
        delete(GameReserveRow).where(GameReserveRow.holder_node_id.in_(vanished)),
        delete(FamineLoreRow).where(FamineLoreRow.people_entity_id.in_(vanished)),
        delete(BrandRow).where(BrandRow.community_entity_id.in_(vanished)),
        update(KeystoneResourceRow).where(KeystoneResourceRow.producer_entity_id.in_(vanished)).values(producer_entity_id=None),
        update(KeystoneResourceRow).where(KeystoneResourceRow.cult_entity_id.in_(vanished)).values(cult_entity_id=None),
        update(KeystoneResourceRow).where(KeystoneResourceRow.controller_entity_id.in_(vanished)).values(controller_entity_id=None),
    ]
    mended = 0
    for statement in statements:
        found = await session.execute(statement)
        mended += int(getattr(found, "rowcount", 0) or 0)
    await session.flush()
    return mended
