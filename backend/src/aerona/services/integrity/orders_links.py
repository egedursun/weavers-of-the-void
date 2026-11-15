from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.honours import NamedUnitRow
from aerona.db.tables.orders import ChainHoldingRow, ExchangeRateRow, HoardRow, OrderTransitionRow, PuttingOutRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.orders import HoardState, TransitionStage


async def mend_orders_links(session: AsyncSession, epoch: int) -> int:
    vanished = select(EntityRow.id).where(EntityRow.status != EntityStatus.CANON)
    open_stages = (TransitionStage.PROCLAIMED, TransitionStage.TRANSFERRING)
    mended = 0
    for statement in (
        update(OrderTransitionRow)
        .where(OrderTransitionRow.stage.in_(open_stages), OrderTransitionRow.polity_entity_id.in_(vanished))
        .values(stage=TransitionStage.FAILED, ended_epoch=epoch),
        update(PuttingOutRow)
        .where(PuttingOutRow.active.is_(True), or_(PuttingOutRow.merchant_entity_id.in_(vanished), PuttingOutRow.town_entity_id.in_(vanished)))
        .values(active=False),
        update(NamedUnitRow)
        .where(NamedUnitRow.disbanded_epoch.is_(None), or_(NamedUnitRow.unit_id.is_(None), NamedUnitRow.owner_entity_id.in_(vanished)))
        .values(disbanded_epoch=epoch, unit_id=None),
        update(ExchangeRateRow).where(ExchangeRateRow.changer_node_id.in_(vanished)).values(changer_node_id=None),
        update(HoardRow).where(HoardRow.state == HoardState.HIDDEN, HoardRow.holder_node_id.in_(vanished)).values(state=HoardState.LOST),
        delete(ChainHoldingRow).where(ChainHoldingRow.holder_entity_id.in_(vanished)),
    ):
        result = await session.execute(statement)
        mended += max(0, getattr(result, "rowcount", 0) or 0)
    return mended
