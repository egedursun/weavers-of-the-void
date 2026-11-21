from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.economy import LoanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import CompanyShareRow
from aerona.db.tables.factions import FactionMembershipRow
from aerona.db.tables.governance import InsolvencyCaseRow, OrgGovernanceRow, OrgMergerRow, OrgSeatRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.governance import OPEN_MERGER_STAGES, GoverningBody, MergerStage
from aerona.engine.governance.seats import apportioned


async def seated(session: AsyncSession, seat: OrgSeatRow) -> bool:
    body = await session.get(OrgGovernanceRow, seat.org_node_id)
    if body is None:
        return False
    if seat.member_node_id == body.head_node_id:
        return True
    if body.decision_body is GoverningBody.SHAREHOLDERS_MEETING:
        return await session.get(CompanyShareRow, (seat.org_node_id, seat.member_node_id)) is not None
    return await session.get(FactionMembershipRow, (seat.org_node_id, seat.member_node_id)) is not None


async def strangers_seated(session: AsyncSession) -> list[int]:
    return [seat.id for seat in await session.scalars(select(OrgSeatRow).order_by(OrgSeatRow.id)) if not await seated(session, seat)]


async def unseat_stranger(session: AsyncSession, key: int) -> None:
    seat = await session.get(OrgSeatRow, key)
    if seat is not None:
        await session.delete(seat)


async def uneven_votes(session: AsyncSession) -> list[int]:
    totals = await session.execute(
        select(OrgSeatRow.org_node_id, func.sum(OrgSeatRow.vote_weight)).group_by(OrgSeatRow.org_node_id).order_by(OrgSeatRow.org_node_id)
    )
    return [org for org, total in totals if int(total or 0) != PERCENT]


async def even_votes(session: AsyncSession, key: int) -> None:
    seats = list(await session.scalars(select(OrgSeatRow).where(OrgSeatRow.org_node_id == key).order_by(OrgSeatRow.member_node_id)))
    weights = apportioned({seat.id: float(max(1, seat.vote_weight)) for seat in seats}, PERCENT)
    for seat in seats:
        seat.vote_weight = weights[seat.id]


async def partyless_mergers(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for merger in await session.scalars(select(OrgMergerRow).where(OrgMergerRow.stage.in_(sorted(OPEN_MERGER_STAGES))).order_by(OrgMergerRow.id)):
        parties = [await session.get(EntityRow, node) for node in (merger.acquirer_node_id, merger.target_node_id)]
        if any(party is None or party.status is not EntityStatus.CANON for party in parties):
            found.append(merger.id)
    return found


async def withdraw_merger(session: AsyncSession, key: int) -> None:
    merger = await session.get(OrgMergerRow, key)
    if merger is not None:
        merger.stage = MergerStage.WITHDRAWN


async def claimless_creditors(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for case in await session.scalars(select(InsolvencyCaseRow).order_by(InsolvencyCaseRow.id)):
        lenders = set(await session.scalars(select(LoanRow.lender_entity_id).where(LoanRow.borrower_entity_id == case.debtor_node_id)))
        if any(creditor not in lenders for creditor in case.creditors or []):
            found.append(case.id)
    return found


async def prune_creditors(session: AsyncSession, key: int) -> None:
    case = await session.get(InsolvencyCaseRow, key)
    if case is None:
        return
    lenders = set(await session.scalars(select(LoanRow.lender_entity_id).where(LoanRow.borrower_entity_id == case.debtor_node_id)))
    case.creditors = [creditor for creditor in case.creditors or [] if creditor in lenders]
