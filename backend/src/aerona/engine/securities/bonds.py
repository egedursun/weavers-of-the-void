from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.cycles import LongPlanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.finance import CreditProfileRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.securities import IssuedSecurityRow, SecurityHoldingRow
from aerona.db.write_guard import held
from aerona.domain.enums.cycles import LongPlanKind, LongPlanStatus
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.securities import SecurityKind
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import give_coin, take_coin
from aerona.engine.recording.record import record
from aerona.engine.sacred.places import at_war, ruler_of
from aerona.engine.securities.exchanges import bank_in, exchange_at, home_town
from aerona.engine.securities.holdings import SecuritiesTally

BOND_COUPON = 5


async def building(ctx: TickContext, realm_id: int) -> bool:
    ruler = await ruler_of(ctx.session, realm_id)
    holders = [realm_id] if ruler is None else [realm_id, ruler]
    query = select(LongPlanRow.id).where(
        LongPlanRow.holder_node_id.in_(holders), LongPlanRow.kind == LongPlanKind.WONDER, LongPlanRow.status == LongPlanStatus.ACTIVE
    )
    return await ctx.session.scalar(query.limit(1)) is not None


async def bond_open(ctx: TickContext, realm_id: int) -> bool:
    query = select(IssuedSecurityRow.id).where(
        IssuedSecurityRow.issuer_node_id == realm_id,
        IssuedSecurityRow.kind == SecurityKind.BOND,
        IssuedSecurityRow.loan_id.is_(None),
        IssuedSecurityRow.delisted_epoch.is_(None),
        IssuedSecurityRow.defaulted_epoch.is_(None),
    )
    return await ctx.session.scalar(query.limit(1)) is not None


async def needs_bonds(ctx: TickContext, realm: EntityRow, profile: PolityProfileRow) -> bool:
    if profile.treasury >= ctx.rules.securities.bond_treasury_below or await bond_open(ctx, realm.id):
        return False
    return await at_war(ctx.session, realm.id) or await building(ctx, realm.id)


async def issue_bonds(ctx: TickContext, tally: SecuritiesTally) -> None:
    table = ctx.rules.securities
    query = select(EntityRow, PolityProfileRow).join(PolityProfileRow, PolityProfileRow.polity_entity_id == EntityRow.id)
    rows = (await ctx.session.execute(query.where(EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id))).all()
    for realm, profile in rows:
        if held(realm.id) or not await needs_bonds(ctx, realm, profile):
            continue
        town_id = await home_town(ctx, realm.id)
        exchange = await exchange_at(ctx, town_id)
        town = await ctx.session.get(EntityRow, town_id) if town_id is not None else None
        buyer = await bank_in(ctx, town) if town is not None else None
        raised = table.bond_amount * table.bond_face
        if exchange is None or buyer is None or held(buyer.id) or not await take_coin(ctx.session, ctx.rules, buyer, raised):
            continue
        credit = await ctx.session.get(CreditProfileRow, realm.id)
        bond = IssuedSecurityRow(
            name=f"the bonds of {realm.name} from epoch {ctx.epoch}",
            issuer_node_id=realm.id,
            kind=SecurityKind.BOND,
            amount=table.bond_amount,
            face_value=table.bond_face,
            coupon_pct=min(PERCENT, credit.interest_pct if credit is not None else BOND_COUPON),
            maturity_epoch=ctx.epoch + table.bond_term_epochs,
            exchange_id=exchange.id,
            price=table.bond_face,
            listed_epoch=ctx.epoch,
            locked=[],
        )
        ctx.session.add(bond)
        await ctx.session.flush()
        ctx.session.add(SecurityHoldingRow(holder_node_id=buyer.id, security_id=bond.id, amount=bond.amount, bought_price=table.bond_face, locked=[]))
        await give_coin(ctx.session, ctx.rules, realm, raised)
        tally.bonds += 1
        await record(
            ctx,
            "securities.bond_issued",
            roles={IncidentRole.BORROWER: realm.id, IncidentRole.LENDER: buyer.id},
            facts={"security": bond.name, "amount": bond.amount, "coupon": bond.coupon_pct},
        )
