from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.finance import OWED_LOANS
from aerona.constants.units import PERCENT
from aerona.db.tables.economy import LoanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import CompanyProfileRow, CompanyShareRow
from aerona.db.tables.governance import InsolvencyCaseRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import LoanStatus
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.governance import OPEN_INSOLVENCY_STAGES, InsolvencyPath, InsolvencyStage
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import DebtRemedy
from aerona.engine.context import TickContext
from aerona.engine.economy.debt_law import debt_law_of
from aerona.engine.economy.purse import coin_of, give_coin, points_of, shift_points, take_coin
from aerona.engine.factions.companies import realm_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.records import retire_in
from aerona.engine.recording.record import record
from aerona.engine.services.community_relations import change_relation

STAGE_LOCK = "stage"
REMEDY_PATHS = {
    DebtRemedy.BONDAGE: InsolvencyPath.SEIZURE_BY_CREDITOR,
    DebtRemedy.PRISON: InsolvencyPath.LIQUIDATION,
    DebtRemedy.JUBILEE: InsolvencyPath.RESTRUCTURING,
}


@dataclass
class InsolvencyTally:
    filed: int = 0
    liquidated: int = 0
    restructured: int = 0
    rescued: int = 0
    seized: int = 0
    defaulted: int = 0


async def open_loans(ctx: TickContext, debtor_id: int) -> list[LoanRow]:
    rows = await ctx.session.scalars(
        select(LoanRow).where(LoanRow.borrower_entity_id == debtor_id, LoanRow.status.in_(OWED_LOANS), LoanRow.held.is_(False)).order_by(LoanRow.id)
    )
    return list(rows)


async def case_of(ctx: TickContext, debtor_id: int) -> InsolvencyCaseRow | None:
    return await ctx.session.scalar(
        select(InsolvencyCaseRow)
        .where(InsolvencyCaseRow.debtor_node_id == debtor_id, InsolvencyCaseRow.stage.in_(sorted(OPEN_INSOLVENCY_STAGES)))
        .order_by(InsolvencyCaseRow.id)
        .limit(1)
    )


async def path_for(ctx: TickContext, debtor: EntityRow, loans: list[LoanRow]) -> InsolvencyPath:
    creditor = await ctx.session.get(EntityRow, loans[0].lender_entity_id) if loans else None
    law = await debt_law_of(ctx, debtor, creditor) if creditor is not None else None
    if law is not None:
        return REMEDY_PATHS[law.remedy]
    owners = list(
        await ctx.session.scalars(select(CompanyShareRow).where(CompanyShareRow.company_entity_id == debtor.id).order_by(CompanyShareRow.share.desc()))
    )
    owed = sum(loan.principal - loan.repaid for loan in loans)
    if owners:
        owner = await ctx.session.get(EntityRow, owners[0].holder_node_id)
        if owner is not None and await coin_of(ctx.session, ctx.rules, owner) >= owed > 0:
            return InsolvencyPath.RESCUE_BY_OWNER
    return InsolvencyPath.LIQUIDATION


async def file_case(ctx: TickContext, debtor: EntityRow, path: InsolvencyPath | None, tally: InsolvencyTally) -> InsolvencyCaseRow | None:
    if held(debtor.id) or await case_of(ctx, debtor.id) is not None:
        return None
    loans = await open_loans(ctx, debtor.id)
    court = await realm_of(ctx, debtor.location_id)
    case = InsolvencyCaseRow(
        debtor_node_id=debtor.id,
        creditors=sorted({loan.lender_entity_id for loan in loans}),
        owed=sum(max(0, loan.principal - loan.repaid) for loan in loans),
        assets=await coin_of(ctx.session, ctx.rules, debtor),
        path=path or await path_for(ctx, debtor, loans),
        court_node_id=court,
        stage=InsolvencyStage.FILED,
        started_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(case)
    await ctx.session.flush()
    await record(
        ctx,
        "org.insolvent",
        roles={IncidentRole.SUBJECT: debtor.id} | ({IncidentRole.AUTHORITY: court} if court is not None else {}),
        facts={"owed": case.owed, "path": case.path},
    )
    tally.filed += 1
    return case


async def default_loans(ctx: TickContext, debtor: EntityRow, share_left_pct: int, tally: InsolvencyTally) -> None:
    table = ctx.rules.banking
    for loan in await open_loans(ctx, debtor.id):
        lender = await ctx.session.get(EntityRow, loan.lender_entity_id)
        loan.status = LoanStatus.DEFAULTED
        if lender is not None and not held(lender.id):
            loss = round_half_up(table.default_bank_loss * (PERCENT - share_left_pct) / PERCENT)
            await shift_points(ctx.session, lender, -loss)
            await change_relation(ctx, lender.id, debtor.id, -table.default_relation_loss, MemoryKind.BETRAYED_ME, note="a debtor failed owing a loan")
        tally.defaulted += 1


async def pay_creditors(ctx: TickContext, case: InsolvencyCaseRow, debtor: EntityRow) -> int:
    floor = ctx.rules.governance.creditor_recovery_floor_pct
    share = clamp_int(round_half_up(case.assets * PERCENT / case.owed) if case.owed > 0 else PERCENT, floor, PERCENT)
    paid_out = min(case.assets, round_half_up(case.owed * share / PERCENT))
    if not await take_coin(ctx.session, ctx.rules, debtor, paid_out):
        paid_out = 0
    loans = await open_loans(ctx, debtor.id)
    owed = sum(max(0, loan.principal - loan.repaid) for loan in loans)
    for loan in loans:
        lender = await ctx.session.get(EntityRow, loan.lender_entity_id)
        portion = round_half_up(paid_out * max(0, loan.principal - loan.repaid) / owed) if owed > 0 else 0
        if lender is not None and not held(lender.id) and portion > 0:
            await give_coin(ctx.session, ctx.rules, lender, portion)
            loan.repaid = min(loan.principal, loan.repaid + portion)
    return share


async def liquidate(ctx: TickContext, case: InsolvencyCaseRow, debtor: EntityRow, tally: InsolvencyTally) -> None:
    loss = ctx.rules.companies.collapse_loss
    for share in await ctx.session.scalars(
        select(CompanyShareRow).where(CompanyShareRow.company_entity_id == debtor.id).order_by(CompanyShareRow.holder_node_id)
    ):
        holder = await ctx.session.get(EntityRow, share.holder_node_id)
        if holder is not None and not held(holder.id):
            await shift_points(ctx.session, holder, -min(loss, await points_of(ctx.session, holder)))
    await default_loans(ctx, debtor, case.recovered_pct, tally)
    company = await ctx.session.get(CompanyProfileRow, debtor.id) is not None
    await retire_in(ctx, debtor, "it failed and its holdings were sold to its creditors", close_bonds=True)
    if company:
        await record(ctx, "companies.collapsed", roles={IncidentRole.SUBJECT: debtor.id}, facts={"loss_per_holder": loss}, place=debtor.location_id)
    else:
        await record(ctx, "org.liquidated", roles={IncidentRole.SUBJECT: debtor.id}, facts={"recovered": case.recovered_pct})
    tally.liquidated += 1


async def restructure(ctx: TickContext, case: InsolvencyCaseRow, debtor: EntityRow, tally: InsolvencyTally) -> None:
    for loan in await open_loans(ctx, debtor.id):
        if loan.repaid >= loan.principal:
            loan.status = LoanStatus.REPAID
        else:
            loan.due_epoch = max(loan.due_epoch, ctx.epoch) + ctx.rules.governance.term_epochs
    await record(ctx, "org.restructured", roles={IncidentRole.SUBJECT: debtor.id}, facts={"recovered": case.recovered_pct, "path": case.path})
    tally.restructured += 1


async def rescue(ctx: TickContext, case: InsolvencyCaseRow, debtor: EntityRow, tally: InsolvencyTally) -> bool:
    if case.path is InsolvencyPath.RESCUE_BY_POLITY:
        rescuer_id = case.court_node_id
    else:
        top = await ctx.session.scalar(
            select(CompanyShareRow.holder_node_id).where(CompanyShareRow.company_entity_id == debtor.id).order_by(CompanyShareRow.share.desc()).limit(1)
        )
        rescuer_id = top
    rescuer = await ctx.session.get(EntityRow, rescuer_id) if rescuer_id is not None else None
    left = max(0, case.owed - round_half_up(case.owed * case.recovered_pct / PERCENT))
    if rescuer is None or held(rescuer.id) or not await take_coin(ctx.session, ctx.rules, rescuer, left):
        return False
    for loan in await open_loans(ctx, debtor.id):
        lender = await ctx.session.get(EntityRow, loan.lender_entity_id)
        if lender is not None and not held(lender.id):
            await give_coin(ctx.session, ctx.rules, lender, round_half_up(left * max(0, loan.principal - loan.repaid) / max(1, case.owed)))
        loan.repaid, loan.status = loan.principal, LoanStatus.REPAID
    await record(
        ctx, "org.restructured", roles={IncidentRole.SUBJECT: debtor.id, IncidentRole.ALLY: rescuer.id}, facts={"recovered": PERCENT, "path": case.path}
    )
    tally.rescued += 1
    return True


async def seize(ctx: TickContext, case: InsolvencyCaseRow, debtor: EntityRow, tally: InsolvencyTally) -> bool:
    creditor_id = case.creditors[0] if case.creditors else None
    creditor = await ctx.session.get(EntityRow, creditor_id) if creditor_id is not None else None
    if creditor is None or held(creditor.id):
        return False
    for share in list(await ctx.session.scalars(select(CompanyShareRow).where(CompanyShareRow.company_entity_id == debtor.id))):
        if not share.locked:
            await ctx.session.delete(share)
    await ctx.session.flush()
    ctx.session.add(CompanyShareRow(company_entity_id=debtor.id, holder_node_id=creditor.id, share=PERCENT, locked=False))
    for loan in await open_loans(ctx, debtor.id):
        if loan.lender_entity_id == creditor.id:
            loan.status = LoanStatus.DEFAULTED
    await record(
        ctx,
        "org.restructured",
        roles={IncidentRole.SUBJECT: debtor.id, IncidentRole.ACTOR: creditor.id},
        facts={"recovered": case.recovered_pct, "path": case.path},
    )
    tally.seized += 1
    return True


async def settle(ctx: TickContext, case: InsolvencyCaseRow, debtor: EntityRow, tally: InsolvencyTally) -> None:
    if case.path is InsolvencyPath.LIQUIDATION:
        await liquidate(ctx, case, debtor, tally)
    elif case.path is InsolvencyPath.RESTRUCTURING:
        await restructure(ctx, case, debtor, tally)
    elif case.path in (InsolvencyPath.RESCUE_BY_OWNER, InsolvencyPath.RESCUE_BY_POLITY):
        if not await rescue(ctx, case, debtor, tally):
            await liquidate(ctx, case, debtor, tally)
    elif not await seize(ctx, case, debtor, tally):
        await liquidate(ctx, case, debtor, tally)


async def advance_case(ctx: TickContext, case: InsolvencyCaseRow, tally: InsolvencyTally) -> bool:
    debtor = await ctx.session.get(EntityRow, case.debtor_node_id)
    if debtor is None or held(debtor.id) or STAGE_LOCK in (case.locked or []):
        return False
    if debtor.status is not EntityStatus.CANON:
        case.stage, case.ended_epoch = InsolvencyStage.CLOSED, ctx.epoch
        return True
    if case.stage is InsolvencyStage.FILED:
        loans = await open_loans(ctx, debtor.id)
        case.creditors = sorted({loan.lender_entity_id for loan in loans})
        case.owed = sum(max(0, loan.principal - loan.repaid) for loan in loans)
        case.assets = await coin_of(ctx.session, ctx.rules, debtor)
        case.stage = InsolvencyStage.CLAIMS
        return True
    if case.stage is InsolvencyStage.CLAIMS:
        case.recovered_pct = await pay_creditors(ctx, case, debtor)
        case.stage = InsolvencyStage.SETTLED
        return True
    await settle(ctx, case, debtor, tally)
    case.stage, case.ended_epoch = InsolvencyStage.CLOSED, ctx.epoch
    return True


async def tend_insolvency(ctx: TickContext, tally: InsolvencyTally) -> int:
    advanced = 0
    for case in list(
        await ctx.session.scalars(select(InsolvencyCaseRow).where(InsolvencyCaseRow.stage.in_(sorted(OPEN_INSOLVENCY_STAGES))).order_by(InsolvencyCaseRow.id))
    ):
        advanced += 1 if await advance_case(ctx, case, tally) else 0
    await ctx.session.flush()
    return advanced
