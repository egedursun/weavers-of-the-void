from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.cycles import (
    CampRow,
    CircuitRow,
    ConfederationRow,
    GiftRow,
    IndentureRow,
    KinshipSystemRow,
    LongPlanRow,
    PeopleReproductionRow,
    SlaveMarketRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.cycles import GiftState, LongPlanStatus
from aerona.domain.enums.entity import EntityStatus

MEMBERS = 2


async def trim_lists(session: AsyncSession, gone: set[int], epoch: int) -> int:
    mended = 0
    for circuit in await session.scalars(select(CircuitRow)):
        kept = [stop for stop in circuit.stops if stop not in gone]
        if kept != circuit.stops:
            circuit.stops = kept
            circuit.position = 0
            mended += 1
    for camp in await session.scalars(select(CampRow)):
        kept = [region for region in camp.circuit if region not in gone]
        if kept != camp.circuit:
            camp.circuit = kept
            camp.season_index = 0
            mended += 1
    for league in await session.scalars(select(ConfederationRow).where(ConfederationRow.dissolved_epoch.is_(None))):
        kept = [member for member in league.members if member not in gone]
        if kept != league.members:
            league.members = kept
            mended += 1
        if len(league.members) < MEMBERS:
            league.dissolved_epoch = epoch
            mended += 1
    return mended


async def mend_cycle_links(session: AsyncSession, epoch: int) -> int:
    vanished = select(EntityRow.id).where(EntityRow.status != EntityStatus.CANON)
    statements = [
        update(LongPlanRow)
        .where(LongPlanRow.status == LongPlanStatus.ACTIVE, LongPlanRow.holder_node_id.in_(vanished))
        .values(status=LongPlanStatus.ABANDONED, finished_epoch=epoch),
        update(GiftRow)
        .where(GiftRow.state.in_([GiftState.OPEN, GiftState.DESTROYED]), GiftRow.receiver_node_id.in_(vanished))
        .values(state=GiftState.LAPSED, settled_epoch=epoch),
        delete(IndentureRow).where(IndentureRow.community_entity_id.in_(vanished)),
        update(SlaveMarketRow).where(SlaveMarketRow.open.is_(True), SlaveMarketRow.settlement_entity_id.in_(vanished)).values(open=False),
        delete(KinshipSystemRow).where(KinshipSystemRow.people_entity_id.in_(vanished)),
        delete(PeopleReproductionRow).where(PeopleReproductionRow.people_entity_id.in_(vanished)),
    ]
    mended = 0
    for statement in statements:
        found = await session.execute(statement)
        mended += int(getattr(found, "rowcount", 0) or 0)
    gone = set(await session.scalars(vanished))
    mended += await trim_lists(session, gone, epoch)
    await session.flush()
    return mended
