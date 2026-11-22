from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.economy import LoanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.securities import IssuedSecurityRow, SecurityHoldingRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import LoanStatus
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.securities import DEBT_KINDS, SecurityKind
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import give_coin, take_coin
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record
from aerona.engine.securities.holdings import SecuritiesTally, holdings_of
from aerona.engine.securities.pricing import traded

FACE_REPAID = frozenset({SecurityKind.BOND, SecurityKind.NOTE})
COUPON_AT_MATURITY = frozenset({SecurityKind.NOTE})
PAID_EACH_EPOCH = frozenset({SecurityKind.BOND, SecurityKind.ANNUITY})


async def mirror_loans(ctx: TickContext, tally: SecuritiesTally) -> None:
    face = ctx.rules.securities.bond_face
    mirrored = select(IssuedSecurityRow.loan_id).where(IssuedSecurityRow.loan_id.is_not(None))
    realms = select(PolityProfileRow.polity_entity_id)
    query = select(LoanRow).where(LoanRow.status == LoanStatus.OPEN, LoanRow.borrower_entity_id.in_(realms), LoanRow.id.not_in(mirrored)).order_by(LoanRow.id)
    for loan in await ctx.session.scalars(query):
        realm = await ctx.session.get(EntityRow, loan.borrower_entity_id)
        if realm is None or held(realm.id) or held(loan.lender_entity_id):
            continue
        bond = IssuedSecurityRow(
            name=f"the bonds of {realm.name} from epoch {loan.issued_epoch}",
            issuer_node_id=realm.id,
            kind=SecurityKind.BOND,
            amount=max(1, loan.principal // face),
            face_value=face,
            coupon_pct=min(PERCENT, loan.interest_pct),
            maturity_epoch=loan.due_epoch,
            loan_id=loan.id,
            price=face,
            listed_epoch=ctx.epoch,
            locked=[],
        )
        ctx.session.add(bond)
        await ctx.session.flush()
        ctx.session.add(SecurityHoldingRow(holder_node_id=loan.lender_entity_id, security_id=bond.id, amount=bond.amount, bought_price=face, locked=[]))
        await traded(ctx, bond, bond.amount)
        tally.bonds += 1
        await record(
            ctx,
            "securities.bond_issued",
            roles={IncidentRole.BORROWER: realm.id, IncidentRole.LENDER: loan.lender_entity_id},
            facts={"security": bond.name, "amount": bond.amount, "coupon": bond.coupon_pct},
        )


async def default_bond(ctx: TickContext, bond: IssuedSecurityRow, why: str, tally: SecuritiesTally) -> None:
    bond.defaulted_epoch = ctx.epoch
    tally.defaults += 1
    await record(
        ctx,
        "securities.bond_defaulted",
        roles={IncidentRole.BORROWER: bond.issuer_node_id},
        facts={"security": bond.name, "why": why, "rate_rise": ctx.rules.securities.default_rate_rise},
    )


async def mature(ctx: TickContext, bond: IssuedSecurityRow, tally: SecuritiesTally) -> None:
    bond.delisted_epoch = ctx.epoch
    tally.matured += 1
    await record(
        ctx, "securities.delisted", roles={IncidentRole.SUBJECT: bond.issuer_node_id}, facts={"security": bond.name, "why": "it fell due and was paid"}
    )


async def follow_loan(ctx: TickContext, bond: IssuedSecurityRow, tally: SecuritiesTally) -> None:
    loan = await ctx.session.get(LoanRow, bond.loan_id) if bond.loan_id is not None else None
    if loan is None:
        return
    if loan.status is LoanStatus.DEFAULTED:
        await default_bond(ctx, bond, "the crown would not pay", tally)
    elif loan.status in (LoanStatus.REPAID, LoanStatus.FORGIVEN):
        await mature(ctx, bond, tally)
    else:
        rows = await holdings_of(ctx.session, bond.id)
        if rows and rows[0].holder_node_id != loan.lender_entity_id and not held(rows[0].holder_node_id):
            loan.lender_entity_id = rows[0].holder_node_id


def owed_now(ctx: TickContext, bond: IssuedSecurityRow, amount: int, *, maturing: bool) -> int:
    coupon = round_half_up(amount * bond.face_value * bond.coupon_pct / PERCENT)
    if bond.kind in COUPON_AT_MATURITY:
        coupon = coupon * max(1, ctx.epoch - bond.listed_epoch) if maturing else 0
    elif bond.kind not in PAID_EACH_EPOCH:
        coupon = 0
    face = amount * bond.face_value if maturing and bond.kind in FACE_REPAID else 0
    return coupon + face


async def pay_coupons(ctx: TickContext, bond: IssuedSecurityRow, issuer: EntityRow, tally: SecuritiesTally) -> None:
    rows = await holdings_of(ctx.session, bond.id)
    maturing = bond.maturity_epoch is not None and ctx.epoch >= bond.maturity_epoch
    due = sum(owed_now(ctx, bond, row.amount, maturing=maturing) for row in rows if row.holder_node_id != issuer.id)
    if due and not await take_coin(ctx.session, ctx.rules, issuer, due):
        await default_bond(ctx, bond, "its issuer could not pay what fell due", tally)
        return
    for row in rows:
        holder = await living_entity(ctx.session, row.holder_node_id)
        if holder is None or holder.id == issuer.id:
            continue
        await give_coin(ctx.session, ctx.rules, holder, owed_now(ctx, bond, row.amount, maturing=maturing))
    if maturing:
        await mature(ctx, bond, tally)


async def tend_debts(ctx: TickContext, tally: SecuritiesTally) -> None:
    query = select(IssuedSecurityRow).where(
        IssuedSecurityRow.kind.in_(sorted(DEBT_KINDS)), IssuedSecurityRow.defaulted_epoch.is_(None), IssuedSecurityRow.delisted_epoch.is_(None)
    )
    for bond in list(await ctx.session.scalars(query.order_by(IssuedSecurityRow.id))):
        issuer = await living_entity(ctx.session, bond.issuer_node_id)
        if issuer is None or held(bond.issuer_node_id) or "defaulted_epoch" in (bond.locked or []):
            continue
        if bond.loan_id is not None:
            await follow_loan(ctx, bond, tally)
        else:
            await pay_coupons(ctx, bond, issuer, tally)
