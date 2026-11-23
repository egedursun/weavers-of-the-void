from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.finance import LOAN_STATES, OWED_LOANS
from aerona.catalog.life.finance import ALLIANCES, BURDENED_STATES
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.economy import LoanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.finance import CreditProfileRow
from aerona.db.tables.polity import PolityProfileRow, TreatyPartyRow, TreatyProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.economy import LoanStatus
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.finance import CreditState
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import coin_of, give_coin, take_coin
from aerona.engine.finance.credit import credit_row, owed, realm_of
from aerona.engine.polity.signatories import realm_of_party, signatories_of
from aerona.engine.primitives.queries import close, connect
from aerona.engine.recording.record import record
from aerona.engine.services.community_relations import change_relation


@dataclass
class DebtTally:
    rescued: int = 0
    repudiated: int = 0
    rescheduled: int = 0
    sold: int = 0
    seized: int = 0
    paid: int = 0


async def open_loans(ctx: TickContext, borrower_id: int) -> list[LoanRow]:
    return list(
        await ctx.session.scalars(
            select(LoanRow).where(LoanRow.borrower_entity_id == borrower_id, LoanRow.status.in_(OWED_LOANS), LoanRow.held.is_(False)).order_by(LoanRow.id)
        )
    )


async def rescue(ctx: TickContext, debtor: EntityRow, rescuer: EntityRow, terms: int, *, by: int | None = None) -> CreditProfileRow:
    row = await credit_row(ctx, debtor.id)
    if "state" not in (row.locked or []):
        row.state = CreditState.RESCUED
    row.rescuer_node_id, row.rescue_terms = rescuer.id, terms
    roles = {IncidentRole.SUBJECT: debtor.id, IncidentRole.PATRON: rescuer.id}
    if by is not None:
        roles[IncidentRole.ACTOR] = by
    await record(ctx, "credit.rescued", roles=roles, facts={"terms": terms})
    return row


async def repudiate(ctx: TickContext, debtor: EntityRow, *, by: int | None = None) -> int:
    row = await credit_row(ctx, debtor.id)
    voided = 0
    lenders: set[int] = set()
    for loan in await open_loans(ctx, debtor.id):
        loan.status = LoanStatus.DEFAULTED
        lenders.add(loan.lender_entity_id)
        voided += owed(loan)
    if "state" not in (row.locked or []):
        row.state = CreditState.REPUDIATED
        row.repudiated_until = ctx.epoch + ctx.rules.credit.epochs(ctx.rules.credit.repudiation_years)
    realm = await realm_of(ctx, debtor.id)
    for lender in sorted(lenders):
        lender_realm = await realm_of(ctx, lender)
        if realm is not None and lender_realm is not None and lender_realm != realm and not held(lender_realm):
            await change_relation(ctx, lender_realm, realm, -ctx.rules.credit.repudiate_grievance, MemoryKind.ILL_WILL, note="voided what it owed")
    roles: dict[IncidentRole, int | list[int]] = {IncidentRole.SUBJECT: debtor.id, IncidentRole.VICTIM: sorted(lenders)}
    if by is not None:
        roles[IncidentRole.ACTOR] = by
    await record(ctx, "credit.repudiated", roles=roles, facts={"voided": voided})
    return voided


async def allies_of(ctx: TickContext, realm_id: int) -> list[int]:
    treaties = select(TreatyProfileRow.treaty_entity_id).where(TreatyProfileRow.kind.in_(ALLIANCES))
    mine = select(TreatyPartyRow.treaty_entity_id).where(
        TreatyPartyRow.treaty_entity_id.in_(treaties), TreatyPartyRow.party_node_id.in_(await signatories_of(ctx.session, realm_id))
    )
    found: set[int] = set()
    for party in await ctx.session.scalars(
        select(TreatyPartyRow.party_node_id).where(TreatyPartyRow.treaty_entity_id.in_(mine)).order_by(TreatyPartyRow.party_node_id)
    ):
        ally = await realm_of_party(ctx.session, party)
        if ally is not None and ally != realm_id:
            found.add(ally)
    return sorted(found)


async def rescue_defaults(ctx: TickContext, tally: DebtTally) -> None:
    table = ctx.rules.credit
    for row in list(
        await ctx.session.scalars(select(CreditProfileRow).where(CreditProfileRow.state == CreditState.DEFAULT).order_by(CreditProfileRow.subject_node_id))
    ):
        debtor = await ctx.session.get(EntityRow, row.subject_node_id)
        if debtor is None or held(debtor.id) or debtor.entity_type is not EntityType.POLITY:
            continue
        for ally_id in await allies_of(ctx, debtor.id):
            ally = await ctx.session.get(EntityRow, ally_id)
            if ally is None or held(ally.id) or await coin_of(ctx.session, ctx.rules, ally) <= 0:
                continue
            if ctx.rng(f"credit.rescue.{debtor.id}.{ally.id}.{ctx.epoch}").chance(table.rescue_pct):
                await rescue(ctx, debtor, ally, table.rescue_sovereignty_cut)
                tally.rescued += 1
                break


async def pay_rescuers(ctx: TickContext, tally: DebtTally) -> None:
    table = ctx.rules.credit
    for row in list(
        await ctx.session.scalars(select(CreditProfileRow).where(CreditProfileRow.state == CreditState.RESCUED).order_by(CreditProfileRow.subject_node_id))
    ):
        debtor = await ctx.session.get(EntityRow, row.subject_node_id)
        rescuer = await ctx.session.get(EntityRow, row.rescuer_node_id) if row.rescuer_node_id is not None else None
        if debtor is None or rescuer is None or held(debtor.id):
            continue
        due = await coin_of(ctx.session, ctx.rules, debtor) * row.rescue_terms // PERCENT
        if due > 0 and await take_coin(ctx.session, ctx.rules, debtor, due):
            await give_coin(ctx.session, ctx.rules, rescuer, due)
            tally.paid += due
        await change_relation(ctx, debtor.id, rescuer.id, table.rescue_standing, MemoryKind.GOODWILL, note="carried its debts")
        if not await open_loans(ctx, debtor.id) and "state" not in (row.locked or []):
            row.state, row.rescuer_node_id = CreditState.NORMAL, None


async def repudiations(ctx: TickContext, tally: DebtTally) -> None:
    table = ctx.rules.credit
    for profile in list(await ctx.session.scalars(select(PolityProfileRow).order_by(PolityProfileRow.polity_entity_id))):
        credit = await ctx.session.get(CreditProfileRow, profile.polity_entity_id)
        if credit is None or credit.state not in BURDENED_STATES or held(profile.polity_entity_id):
            continue
        new_ruler = await ctx.session.scalar(
            select(BondRow.id)
            .where(BondRow.target_node_id == profile.polity_entity_id, BondRow.kind == BondKind.RULES, BondRow.epoch >= ctx.epoch - 1)
            .limit(1)
        )
        if new_ruler is None or not ctx.rng(f"credit.repudiate.{profile.polity_entity_id}.{ctx.epoch}").chance(table.repudiate_pct):
            continue
        debtor = await ctx.session.get(EntityRow, profile.polity_entity_id)
        if debtor is not None:
            await repudiate(ctx, debtor)
            tally.repudiated += 1


async def reschedule(ctx: TickContext, loan: LoanRow, extra_epochs: int, *, rate_cut: int = 0, by: int | None = None) -> LoanRow:
    loan.due_epoch += extra_epochs
    loan.interest_pct = max(0, loan.interest_pct - rate_cut)
    loan.status = LoanStatus.RESCHEDULED
    roles = {IncidentRole.SUBJECT: loan.borrower_entity_id, IncidentRole.PATRON: loan.lender_entity_id}
    if by is not None:
        roles[IncidentRole.ACTOR] = by
    await record(ctx, "loan.rescheduled", roles=roles, facts={"epochs": extra_epochs})
    return loan


async def sell(ctx: TickContext, loan: LoanRow, buyer: EntityRow, *, by: int | None = None) -> int:
    seller = await ctx.session.get(EntityRow, loan.lender_entity_id)
    price = owed(loan) * (PERCENT - ctx.rules.credit.sale_discount_pct) // PERCENT
    if seller is None or not await take_coin(ctx.session, ctx.rules, buyer, price):
        return -1
    await give_coin(ctx.session, ctx.rules, seller, price)
    loan.lender_entity_id, loan.status = buyer.id, LoanStatus.SOLD
    roles = {IncidentRole.SUBJECT: loan.borrower_entity_id, IncidentRole.SELLER: seller.id, IncidentRole.BUYER: buyer.id}
    if by is not None:
        roles[IncidentRole.ACTOR] = by
    await record(ctx, "loan.sold", roles=roles, facts={"price": price})
    return price


async def seize_collateral(ctx: TickContext, loan: LoanRow) -> bool:
    pledge = await ctx.session.get(EntityRow, loan.collateral_node_id) if loan.collateral_node_id is not None else None
    if pledge is None or held(pledge.id) or LOAN_STATES[loan.status].owed:
        return False
    for bond in await ctx.session.scalars(
        select(BondRow).where(BondRow.target_node_id == pledge.id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE).order_by(BondRow.id)
    ):
        await close(ctx.session, bond, ctx.epoch, "seized for a debt")
    await connect(ctx.session, loan.lender_entity_id, pledge.id, BondKind.OWNS, ctx.epoch, description="seized for a debt")
    loan.status = LoanStatus.COLLATERAL_SEIZED
    await record(
        ctx,
        "loan.collateral_seized",
        roles={IncidentRole.SUBJECT: loan.borrower_entity_id, IncidentRole.PATRON: loan.lender_entity_id, IncidentRole.TARGET: pledge.id},
    )
    return True


async def ease_strained(ctx: TickContext, tally: DebtTally) -> None:
    table = ctx.rules.credit
    strained = select(CreditProfileRow.subject_node_id).where(CreditProfileRow.state == CreditState.STRAINED)
    for loan in list(
        await ctx.session.scalars(
            select(LoanRow).where(LoanRow.status == LoanStatus.OPEN, LoanRow.held.is_(False), LoanRow.borrower_entity_id.in_(strained)).order_by(LoanRow.id)
        )
    ):
        if held(loan.borrower_entity_id, loan.lender_entity_id) or loan.due_epoch > ctx.epoch + 1:
            continue
        if ctx.rng(f"loan.reschedule.{loan.id}.{ctx.epoch}").chance(table.reschedule_pct):
            await reschedule(ctx, loan, table.epochs(table.reschedule_years))
            tally.rescheduled += 1


async def sell_in_need(ctx: TickContext, tally: DebtTally) -> None:
    table = ctx.rules.credit
    for loan in list(await ctx.session.scalars(select(LoanRow).where(LoanRow.status.in_(OWED_LOANS), LoanRow.held.is_(False)).order_by(LoanRow.id))):
        seller = await ctx.session.get(EntityRow, loan.lender_entity_id)
        if seller is None or held(seller.id) or await coin_of(ctx.session, ctx.rules, seller) > owed(loan):
            continue
        if not ctx.rng(f"loan.sale.{loan.id}.{ctx.epoch}").chance(table.sale_pct):
            continue
        buyers = select(LoanRow.lender_entity_id).where(LoanRow.lender_entity_id != seller.id)
        buyer = await ctx.session.scalar(
            select(EntityRow).where(EntityRow.id.in_(buyers), EntityRow.id != loan.borrower_entity_id).order_by(EntityRow.id).limit(1)
        )
        if buyer is not None and not held(buyer.id) and await sell(ctx, loan, buyer) >= 0:
            tally.sold += 1


async def keep_debts(ctx: TickContext, tally: DebtTally) -> None:
    await repudiations(ctx, tally)
    await rescue_defaults(ctx, tally)
    await pay_rescuers(ctx, tally)
    await ease_strained(ctx, tally)
    await sell_in_need(ctx, tally)
