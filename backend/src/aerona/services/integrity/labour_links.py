from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.labour import LabourContractRow, LabourDisputeRow, WorkerBodyRow
from aerona.domain.enums.demography import Job
from aerona.domain.enums.labour import DisputeOutcome
from aerona.engine.labour.bodies import trade_workers

KNOWN_TRADES = frozenset(job.value for job in Job)


async def bodiless_contracts(session: AsyncSession) -> list[int]:
    query = select(LabourContractRow.id).where(
        LabourContractRow.body_node_id.is_not(None), LabourContractRow.body_node_id.not_in(select(WorkerBodyRow.faction_node_id))
    )
    return list(await session.scalars(query.order_by(LabourContractRow.id)))


async def drop_body(session: AsyncSession, key: int) -> None:
    contract = await session.get(LabourContractRow, key)
    if contract is not None:
        contract.body_node_id = None


async def overfull_disputes(session: AsyncSession) -> list[int]:
    found: list[int] = []
    query = select(LabourDisputeRow).where(LabourDisputeRow.outcome == DisputeOutcome.ONGOING).order_by(LabourDisputeRow.id)
    for dispute in await session.scalars(query):
        if dispute.workers_out > await room_of(session, dispute):
            found.append(dispute.id)
    return found


async def room_of(session: AsyncSession, dispute: LabourDisputeRow) -> int:
    body = await session.get(WorkerBodyRow, dispute.body_node_id) if dispute.body_node_id is not None else None
    works = await trade_workers(session, dispute.settlement_entity_id, [dispute.trade]) if dispute.settlement_entity_id is not None else 0
    return max(works, body.members if body is not None else 0)


async def trim_out(session: AsyncSession, key: int) -> None:
    dispute = await session.get(LabourDisputeRow, key)
    if dispute is not None:
        dispute.workers_out = await room_of(session, dispute)


async def unknown_trades(session: AsyncSession) -> list[int]:
    return [
        body.faction_node_id
        for body in await session.scalars(select(WorkerBodyRow).order_by(WorkerBodyRow.faction_node_id))
        if any(trade not in KNOWN_TRADES for trade in body.trades or [])
    ]


async def drop_unknown_trades(session: AsyncSession, key: int) -> None:
    body = await session.get(WorkerBodyRow, key)
    if body is not None:
        body.trades = [trade for trade in body.trades or [] if trade in KNOWN_TRADES]
