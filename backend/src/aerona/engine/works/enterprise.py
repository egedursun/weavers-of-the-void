from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.works_shapes import ENTERPRISE_REVENUE_PCT, MANAGEMENT_SKIM_PCT
from aerona.constants.units import PERCENT
from aerona.db.tables.commerce import ShopGoodRow, ShopRow
from aerona.db.tables.economy import CurrencyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.orders import EconomicOrderRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.works import StateEnterpriseRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.orders import OwnershipRegime
from aerona.domain.enums.works import EnterpriseForm, EnterpriseManagement
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import give_coin
from aerona.engine.numbers.book import towns_in
from aerona.engine.primitives.mirrors import first_sight
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.recording.record import record

USUAL_CORRUPTION = 50
ORDER_FAMILY = "state_enterprises.order"
STATE_FORMS = {OwnershipRegime.RULER: EnterpriseForm.ROYAL_WORKS, OwnershipRegime.STATE: EnterpriseForm.STATE_COMPANY}


@dataclass
class EnterpriseTally:
    revenue: int = 0
    skimmed: int = 0
    starved: int = 0
    privatised: int = 0
    founded: int = 0


async def starve(ctx: TickContext, enterprise: StateEnterpriseRow, tally: EnterpriseTally) -> None:
    if enterprise.sector is None:
        return
    towns = await towns_in(ctx.session, enterprise.polity_entity_id)
    rivals = await ctx.session.scalars(
        select(ShopRow)
        .join(ShopGoodRow, ShopGoodRow.shop_id == ShopRow.id)
        .where(ShopGoodRow.commodity == enterprise.sector, ShopRow.settlement_entity_id.in_(towns))
        .order_by(ShopRow.id)
    )
    for shop in list(rivals):
        if shop.keeper_node_id == enterprise.manager_node_id or held(shop.keeper_node_id) or "stock" in (shop.locked or []):
            continue
        shop.stock = max(0, shop.stock - ctx.rules.state_enterprise.starve_rivals)
        tally.starved += 1


async def privatise(ctx: TickContext, enterprise: StateEnterpriseRow, realm: PolityProfileRow, tally: EnterpriseTally) -> None:
    if enterprise.management is not EnterpriseManagement.OFFICIAL or realm.treasury > ctx.rules.state_enterprise.privatise_debt:
        return
    if {"management", "manager_node_id"} & set(enterprise.locked or []):
        return
    polity = await ctx.session.get(EntityRow, enterprise.polity_entity_id)
    company = await ctx.session.scalar(
        select(EntityRow)
        .join(FactionProfileRow, FactionProfileRow.faction_entity_id == EntityRow.id)
        .where(
            FactionProfileRow.kind == FactionKind.CHARTERED_COMPANY,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.world_id == (polity.world_id if polity else None),
        )
        .order_by(EntityRow.id)
        .limit(1)
    )
    if company is None or held(company.id):
        return
    enterprise.management, enterprise.manager_node_id = EnterpriseManagement.COMPANY, company.id
    await record(
        ctx,
        "enterprise.privatised",
        roles={IncidentRole.ACTOR: enterprise.polity_entity_id, IncidentRole.TARGET: company.id},
        facts={"form": enterprise.form},
    )
    tally.privatised += 1


async def run_enterprise(ctx: TickContext, enterprise: StateEnterpriseRow, tally: EnterpriseTally) -> None:
    table = ctx.rules.state_enterprise
    realm = await ctx.session.get(PolityProfileRow, enterprise.polity_entity_id)
    revenue = round_half_up(enterprise.output * table.revenue_per_output * ENTERPRISE_REVENUE_PCT[enterprise.form] / PERCENT)
    if enterprise.form is EnterpriseForm.MONOPOLY:
        revenue = round_half_up(revenue * (PERCENT + table.monopoly_price_pct) / PERCENT)
        await starve(ctx, enterprise, tally)
    manager = await ctx.session.get(EntityRow, enterprise.manager_node_id) if enterprise.manager_node_id is not None else None
    odds = table.skim_chance_pct * enterprise.corruption / USUAL_CORRUPTION * MANAGEMENT_SKIM_PCT[enterprise.management] / PERCENT
    if manager is not None and revenue and ctx.rng(f"enterprise_skim.{enterprise.id}.{ctx.epoch}").chance(min(PERCENT, odds)):
        skimmed = round_half_up(revenue * enterprise.corruption / PERCENT)
        revenue -= skimmed
        await give_coin(ctx.session, ctx.rules, manager, skimmed)
        await record(
            ctx,
            "enterprise.skimmed",
            roles={IncidentRole.ACTOR: manager.id, IncidentRole.TARGET: enterprise.polity_entity_id},
            facts={"form": enterprise.form, "amount": skimmed},
        )
        tally.skimmed += skimmed
    if "revenue" not in (enterprise.locked or []):
        enterprise.revenue = revenue
    if realm is not None and "treasury" not in (realm.locked or []):
        realm.treasury += revenue
    tally.revenue += revenue
    if enterprise.form is EnterpriseForm.MINT:
        coin = await ctx.session.scalar(
            select(CurrencyRow).where(CurrencyRow.issuer_entity_id == enterprise.polity_entity_id).order_by(CurrencyRow.id).limit(1)
        )
        if coin is not None and not coin.held:
            coin.supply += enterprise.output
    if realm is not None:
        await privatise(ctx, enterprise, realm, tally)


async def found_for_orders(ctx: TickContext, tally: EnterpriseTally) -> None:
    query = select(EconomicOrderRow).where(EconomicOrderRow.ownership.in_(sorted(STATE_FORMS)), EconomicOrderRow.sector.is_not(None))
    for order in list(await ctx.session.scalars(query.order_by(EconomicOrderRow.id))):
        if held(order.polity_entity_id) or not await first_sight(ctx.session, ORDER_FAMILY, order.id):
            continue
        running = select(StateEnterpriseRow.id).where(StateEnterpriseRow.polity_entity_id == order.polity_entity_id, StateEnterpriseRow.sector == order.sector)
        if await ctx.session.scalar(running.limit(1)) is not None:
            continue
        form = STATE_FORMS[order.ownership]
        ctx.session.add(
            StateEnterpriseRow(
                polity_entity_id=order.polity_entity_id,
                sector=order.sector,
                form=form,
                management=EnterpriseManagement.OFFICIAL,
                output=PERCENT // 10,
                founded_epoch=ctx.epoch,
                locked=[],
            )
        )
        await record(ctx, "enterprise.founded", roles={IncidentRole.ACTOR: order.polity_entity_id}, facts={"form": form})
        tally.founded += 1


async def keep_enterprises(ctx: TickContext) -> EnterpriseTally:
    tally = EnterpriseTally()
    await found_for_orders(ctx, tally)
    for enterprise in list(await ctx.session.scalars(select(StateEnterpriseRow).order_by(StateEnterpriseRow.id))):
        if not held(enterprise.polity_entity_id):
            await run_enterprise(ctx, enterprise, tally)
    await ctx.session.flush()
    return tally
