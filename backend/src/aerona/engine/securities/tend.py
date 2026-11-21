from sqlalchemy import select

from aerona.db.tables.securities import IssuedSecurityRow, StockExchangeRow
from aerona.db.write_guard import held
from aerona.engine.context import TickContext
from aerona.engine.securities.bonds import issue_bonds
from aerona.engine.securities.debts import mirror_loans, tend_debts
from aerona.engine.securities.exchanges import calm, list_unlisted, open_exchanges
from aerona.engine.securities.holdings import SecuritiesTally
from aerona.engine.securities.pricing import move_price
from aerona.engine.securities.shares import apply_legacy, delist_orphans, sync_shares


async def tend_securities(ctx: TickContext) -> SecuritiesTally:
    tally = SecuritiesTally()
    await apply_legacy(ctx, tally)
    await open_exchanges(ctx, tally)
    await mirror_loans(ctx, tally)
    await issue_bonds(ctx, tally)
    await delist_orphans(ctx, tally)
    await list_unlisted(ctx, tally)
    await tend_debts(ctx, tally)
    exchanges = {row.id: row for row in await ctx.session.scalars(select(StockExchangeRow).order_by(StockExchangeRow.id))}
    query = select(IssuedSecurityRow).where(IssuedSecurityRow.delisted_epoch.is_(None)).order_by(IssuedSecurityRow.id)
    for security in list(await ctx.session.scalars(query)):
        if held(security.issuer_node_id):
            continue
        await move_price(ctx, security, exchanges.get(security.exchange_id) if security.exchange_id is not None else None, tally)
    for exchange in exchanges.values():
        if exchange.settlement_entity_id is None or not held(exchange.settlement_entity_id):
            calm(ctx, exchange)
    await sync_shares(ctx, tally)
    return tally
