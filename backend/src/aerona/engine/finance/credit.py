from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.economy import CommunityStockRow, CurrencyRow, LoanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.finance import CreditProfileRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import CommodityKind, LoanStatus
from aerona.domain.enums.finance import CreditState
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.war import WarCause
from aerona.engine.context import TickContext
from aerona.engine.industry.owners import purse_value
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import headcount
from aerona.engine.services.war import declare_war

RESERVE_METALS = (MaterialKind.GOLD, MaterialKind.SILVER)
BASE_RATING = 50
THOUSAND = 1000


@dataclass
class CreditTally:
    rated: int = 0
    strained: int = 0
    restructured: int = 0
    backed: int = 0
    wars: int = 0


def owed(loan: LoanRow) -> int:
    return max(0, round_half_up(loan.principal * (PERCENT + loan.interest_pct) / PERCENT) - loan.repaid)


async def credit_row(ctx: TickContext, subject_id: int) -> CreditProfileRow:
    row = await ctx.session.get(CreditProfileRow, subject_id)
    if row is None:
        row = CreditProfileRow(
            subject_node_id=subject_id, rating=BASE_RATING, state=CreditState.NORMAL, interest_pct=ctx.rules.credit.base_interest, epoch=ctx.epoch, locked=[]
        )
        ctx.session.add(row)
    return row


async def reserves_of(ctx: TickContext, realm_id: int) -> int:
    members = select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == realm_id)
    total = await ctx.session.scalar(
        select(func.coalesce(func.sum(CommunityStockRow.quantity), 0)).where(
            CommunityStockRow.community_entity_id.in_(members), CommunityStockRow.commodity == CommodityKind.ORE, CommunityStockRow.material.in_(RESERVE_METALS)
        )
    )
    return int(total or 0)


async def trust_of(ctx: TickContext, subject_id: int) -> int | None:
    society = await ctx.session.get(CommunitySocietyRow, subject_id)
    if society is None or society.currency_id is None:
        return None
    currency = await ctx.session.get(CurrencyRow, society.currency_id)
    return currency.trust if currency is not None else None


def rated_interest(ctx: TickContext, rating: int, trust: int | None) -> int:
    table = ctx.rules.credit
    scarcity = (PERCENT - trust) * table.supply_pct / PERCENT if trust is not None else 0
    return clamp_int(table.base_interest + (PERCENT - rating) * table.spread_pct / PERCENT + scarcity, 0, PERCENT)


async def borrowers(ctx: TickContext) -> list[int]:
    found = set(await ctx.session.scalars(select(LoanRow.borrower_entity_id)))
    found |= set(await ctx.session.scalars(select(PolityProfileRow.polity_entity_id)))
    found |= set(await ctx.session.scalars(select(CreditProfileRow.subject_node_id)))
    return sorted(found)


async def rate(ctx: TickContext, subject_id: int, tally: CreditTally) -> CreditProfileRow | None:
    if held(subject_id):
        return None
    table = ctx.rules.credit
    loans = list(await ctx.session.scalars(select(LoanRow).where(LoanRow.borrower_entity_id == subject_id)))
    repaid = sum(1 for loan in loans if loan.status is LoanStatus.REPAID)
    defaulted = sum(1 for loan in loans if loan.status is LoanStatus.DEFAULTED)
    debt = sum(owed(loan) for loan in loans if loan.status is LoanStatus.OPEN)
    realm = await ctx.session.get(PolityProfileRow, subject_id)
    if realm is not None:
        debt += realm.debt
    treasury = await purse_value(ctx, subject_id)
    row = await credit_row(ctx, subject_id)
    locked = set(row.locked or [])
    if "defaults" not in locked:
        row.defaults = max(row.defaults or 0, defaulted)
    if "rating" not in locked:
        stability = (realm.stability - PERCENT // 2) if realm is not None else 0
        row.rating = clamp_int(
            BASE_RATING + repaid * table.repay_gain - row.defaults * table.default_loss + treasury / table.treasury_per_point + stability // 2, 0, PERCENT
        )
    if "state" not in locked:
        if row.restructured_until is not None and row.restructured_until >= ctx.epoch:
            row.state = CreditState.RESTRUCTURING
        elif row.state is CreditState.DEFAULT:
            row.state, row.restructured_until = CreditState.RESTRUCTURING, ctx.epoch + table.restructure_epochs
            tally.restructured += 1
        elif debt * PERCENT > max(1, treasury) * table.strained_debt_pct:
            row.state = CreditState.STRAINED
            tally.strained += 1
        else:
            row.state = CreditState.NORMAL
    if "interest_pct" not in locked:
        row.interest_pct = rated_interest(ctx, row.rating, await trust_of(ctx, subject_id))
    if realm is not None and "reserves" not in locked:
        row.reserves = await reserves_of(ctx, subject_id)
    row.epoch = ctx.epoch
    tally.rated += 1
    return row


async def back_currencies(ctx: TickContext, tally: CreditTally) -> None:
    table = ctx.rules.credit
    users: dict[int, int] = defaultdict(int)
    for society in await ctx.session.scalars(select(CommunitySocietyRow).where(CommunitySocietyRow.currency_id.is_not(None))):
        entity = await ctx.session.get(EntityRow, society.entity_id)
        if entity is not None and society.currency_id is not None:
            users[society.currency_id] += headcount(entity)
    for currency in await ctx.session.scalars(select(CurrencyRow).order_by(CurrencyRow.id)):
        row = await ctx.session.get(CreditProfileRow, currency.issuer_entity_id)
        if row is None or currency.held or held(currency.issuer_entity_id):
            continue
        need = max(1, users.get(currency.id, 0) * table.reserve_per_1000 // THOUSAND)
        ratio = row.reserves / need
        shift = table.reserve_trust if ratio >= 1 else -table.reserve_trust if ratio < 1 / 2 else 0
        currency.trust = clamp_int(currency.trust + shift, 0, PERCENT)
        tally.backed += 1


async def interest_for(ctx: TickContext, borrower_id: int, fallback: int) -> int:
    row = await ctx.session.get(CreditProfileRow, borrower_id)
    return row.interest_pct if row is not None else fallback


async def refuses(ctx: TickContext, borrower_id: int) -> bool:
    row = await ctx.session.get(CreditProfileRow, borrower_id)
    return row is not None and row.state in (CreditState.DEFAULT, CreditState.RESTRUCTURING)


async def realm_of(ctx: TickContext, node_id: int | None) -> int | None:
    if node_id is None:
        return None
    if await ctx.session.get(PolityProfileRow, node_id) is not None:
        return node_id
    return await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == node_id).limit(1))


async def on_default(ctx: TickContext, borrower: EntityRow, lender: EntityRow) -> bool:
    table = ctx.rules.credit
    if held(borrower.id):
        return False
    row = await credit_row(ctx, borrower.id)
    if "state" not in (row.locked or []):
        row.state = CreditState.DEFAULT
        row.restructured_until = ctx.epoch + table.restructure_epochs
    if "rating" not in (row.locked or []):
        row.rating = clamp_int(row.rating - table.default_loss, 0, PERCENT)
    row.defaults += 1
    bank = await ctx.session.get(FactionProfileRow, lender.id)
    creditor = await realm_of(ctx, bank.home_entity_id if bank is not None else lender.affiliated_entity_id)
    debtor = await realm_of(ctx, borrower.id)
    if creditor is None or debtor is None or creditor == debtor:
        return False
    if not ctx.rng(f"debt_war.{creditor}.{debtor}.{ctx.epoch}").chance(table.war_chance):
        return False
    return await declare_war(ctx, creditor, debtor, f"to collect what {borrower.name} owes", cause=WarCause.DEBT)


async def tend_credit(ctx: TickContext, tally: CreditTally) -> None:
    for subject_id in await borrowers(ctx):
        await rate(ctx, subject_id, tally)
    await ctx.session.flush()
    await back_currencies(ctx, tally)
