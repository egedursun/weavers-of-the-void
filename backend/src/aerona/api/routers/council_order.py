from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.routers.foundations import current_epoch
from aerona.api.schemas.council_order import CouncilOrderView, CouncilProcedureView, CouncilViolationView, DivineSeatView, GodCouncilView
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.council_order import CouncilProcedureRow, CouncilViolationRow, DivineSeatRow
from aerona.db.tables.divine import CouncilRulingRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.divine import VotingRule
from aerona.engine.divine.council_order import sitting
from aerona.rules.registry import Rules

router = APIRouter(tags=["council"])
NodeId = Annotated[int, Path(ge=1)]


async def procedure_view(session: AsyncSession, rules: Rules, epoch_term: int) -> CouncilProcedureView:
    row = await session.scalar(select(CouncilProcedureRow).order_by(CouncilProcedureRow.id).limit(1))
    if row is None:
        row = CouncilProcedureRow(quorum_pct=50, voting_rule=VotingRule.MAJORITY, creator_veto=True, term_epochs=epoch_term, locked=[])
    return CouncilProcedureView(
        quorum_pct=row.quorum_pct,
        voting_rule=row.voting_rule,
        creator_veto=row.creator_veto,
        term_epochs=row.term_epochs,
        veto_cost=rules.council.veto_attention,
        locked=list(row.locked),
    )


async def violation_views(session: AsyncSession, rows: list[CouncilViolationRow]) -> list[CouncilViolationView]:
    refs = await node_refs(session, sorted({row.violator_node_id for row in rows}))
    ruling_ids = [row.ruling_id for row in rows if row.ruling_id is not None]
    motions = {ruling.id: ruling.motion for ruling in await session.scalars(select(CouncilRulingRow).where(CouncilRulingRow.id.in_(ruling_ids)))}
    return [
        CouncilViolationView(
            id=row.id,
            ruling_id=row.ruling_id,
            ruling_motion=motions.get(row.ruling_id) if row.ruling_id is not None else None,
            violator=refs[row.violator_node_id],
            epoch=row.epoch,
            step=row.step,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def seat_views(session: AsyncSession, rows: list[DivineSeatRow], epoch: int) -> list[DivineSeatView]:
    refs = await node_refs(session, sorted({row.god_node_id for row in rows}))
    sons = set(await session.scalars(select(SonRow.id).where(SonRow.id.in_([row.god_node_id for row in rows]))))
    return [
        DivineSeatView(
            god=refs[row.god_node_id],
            is_son=row.god_node_id in sons,
            seat=row.seat,
            since_epoch=row.since_epoch,
            excluded_until=row.excluded_until,
            sitting=sitting(row, epoch),
            locked=list(row.locked),
        )
        for row in rows
    ]


@router.get("/council/order", response_model=CouncilOrderView)
async def council_order(services: ServicesDep) -> CouncilOrderView:
    async with reader(services) as session:
        rules = services.rules.current
        epoch = await current_epoch(session)
        seats = list(await session.scalars(select(DivineSeatRow).order_by(DivineSeatRow.god_node_id)))
        violations = list(await session.scalars(select(CouncilViolationRow).order_by(CouncilViolationRow.id.desc())))
        return CouncilOrderView(
            procedure=await procedure_view(session, rules, rules.council.ruling_epochs),
            seats=await seat_views(session, seats, epoch),
            violations=await violation_views(session, violations),
        )


@router.get("/council/order/of/{node_id}", response_model=GodCouncilView)
async def god_council(services: ServicesDep, node_id: NodeId) -> GodCouncilView:
    async with reader(services) as session:
        if await session.get(NodeRow, node_id) is None:
            raise NotFoundError("No such thing.")
        epoch = await current_epoch(session)
        refs = await node_refs(session, [node_id])
        is_god = await session.get(SonRow, node_id) is not None or await session.get(ForeignGodRow, node_id) is not None
        seat = await session.get(DivineSeatRow, node_id)
        mine = select(CouncilViolationRow).where(CouncilViolationRow.violator_node_id == node_id)
        rows = list(await session.scalars(mine.order_by(CouncilViolationRow.id.desc())))
        seats = await seat_views(session, [seat], epoch) if seat is not None else []
        return GodCouncilView(node=refs[node_id], is_god=is_god, seat=seats[0] if seats else None, violations=await violation_views(session, rows))
