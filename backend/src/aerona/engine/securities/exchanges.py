from sqlalchemy import select

from aerona.db.faction_kinds import of_kinds
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.securities import IssuedSecurityRow, StockExchangeRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import LENDER_KINDS
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.lore.research import lacks
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import record
from aerona.engine.securities.holdings import SecuritiesTally


async def exchange_at(ctx: TickContext, town_id: int | None) -> StockExchangeRow | None:
    if town_id is None:
        return None
    query = select(StockExchangeRow).where(StockExchangeRow.settlement_entity_id == town_id).order_by(StockExchangeRow.id).limit(1)
    return await ctx.session.scalar(query)


async def bank_in(ctx: TickContext, town: EntityRow) -> EntityRow | None:
    query = select(EntityRow).where(
        EntityRow.entity_type == EntityType.FACTION,
        of_kinds(LENDER_KINDS),
        EntityRow.status == EntityStatus.CANON,
        EntityRow.location_id == town.id,
    )
    banks = [bank for bank in await ctx.session.scalars(query.order_by(EntityRow.id)) if stat_or(bank, "wealth", 0) >= ctx.rules.banking.bank_wealth]
    return max(banks, key=lambda bank: (stat_or(bank, "wealth", 0), -bank.id)) if banks else None


async def open_exchanges(ctx: TickContext, tally: SecuritiesTally) -> None:
    table = ctx.rules.securities
    query = select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    for town in await ctx.session.scalars(query):
        if held(town.id) or stat_or(town, "population", 0) < table.exchange_min_population or await exchange_at(ctx, town.id) is not None:
            continue
        bank = await bank_in(ctx, town)
        if bank is None or await lacks(ctx.session, town.id, Technique.BANKING):
            continue
        if not ctx.rng(f"securities.exchange.{town.id}.{ctx.epoch}").chance(table.exchange_chance_pct):
            continue
        exchange = StockExchangeRow(
            name=f"the exchange of {town.name}", settlement_entity_id=town.id, owner_node_id=bank.id, members=[bank.id], founded_epoch=ctx.epoch, locked=[]
        )
        ctx.session.add(exchange)
        await ctx.session.flush()
        tally.opened += 1
        await record(
            ctx,
            "securities.exchange_opened",
            roles={IncidentRole.OWNER: bank.id, IncidentRole.PLACE: town.id},
            facts={"exchange": exchange.name},
            place=town.id,
        )


async def home_town(ctx: TickContext, issuer_id: int) -> int | None:
    issuer = await ctx.session.get(EntityRow, issuer_id)
    if issuer is None:
        return None
    if issuer.entity_type is EntityType.SETTLEMENT:
        return issuer.id
    realm = await ctx.session.get(PolityProfileRow, issuer.id) if issuer.entity_type is EntityType.POLITY else None
    if realm is not None:
        return realm.capital_entity_id
    return issuer.location_id or issuer.affiliated_entity_id


async def list_on(ctx: TickContext, security: IssuedSecurityRow, exchange: StockExchangeRow) -> None:
    security.exchange_id = exchange.id
    await record(
        ctx,
        "securities.listed",
        roles={IncidentRole.ACTOR: security.issuer_node_id, IncidentRole.PLACE: exchange.settlement_entity_id},
        facts={"security": security.name, "kind": security.kind, "amount": security.amount, "exchange": exchange.name},
        place=exchange.settlement_entity_id,
    )


async def list_unlisted(ctx: TickContext, tally: SecuritiesTally) -> None:
    query = select(IssuedSecurityRow).where(IssuedSecurityRow.exchange_id.is_(None), IssuedSecurityRow.delisted_epoch.is_(None)).order_by(IssuedSecurityRow.id)
    for security in await ctx.session.scalars(query):
        if held(security.issuer_node_id) or "exchange_id" in (security.locked or []):
            continue
        exchange = await exchange_at(ctx, await home_town(ctx, security.issuer_node_id))
        if exchange is None:
            continue
        await list_on(ctx, security, exchange)
        tally.listed += 1


def calm(ctx: TickContext, exchange: StockExchangeRow) -> None:
    if "mood" in (exchange.locked or []) or not exchange.mood:
        return
    step = min(ctx.rules.securities.mood_decay, abs(exchange.mood))
    exchange.mood += -step if exchange.mood > 0 else step
