from sqlalchemy import select

from aerona.agents.context.scope import Scope
from aerona.core.grammar import several, spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.governance import OrgGovernanceRow
from aerona.db.tables.securities import IssuedSecurityRow, SecurityHoldingRow, StockExchangeRow

TOP_LISTED = 5


def security_line(security: IssuedSecurityRow) -> str:
    state = ", a bubble" if security.bubble else ", defaulted" if security.defaulted_epoch is not None else ""
    return f"{security.name} (security {security.id}, {spoken(security.kind)}) at {security.price}{state}"


async def mortal_securities_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    exchanges = select(StockExchangeRow).where(StockExchangeRow.settlement_entity_id == me.location_id).order_by(StockExchangeRow.id)
    for exchange in await session.scalars(exchanges):
        listed = select(IssuedSecurityRow).where(IssuedSecurityRow.exchange_id == exchange.id, IssuedSecurityRow.delisted_epoch.is_(None))
        top = list(await session.scalars(listed.order_by(IssuedSecurityRow.price.desc(), IssuedSecurityRow.id).limit(TOP_LISTED)))
        names = "; ".join(security_line(security) for security in top) or "nothing listed"
        found.append(f"{exchange.name} (exchange {exchange.id}), mood {exchange.mood}, margin {exchange.margin_pct}: {names}")
    headed = set(await session.scalars(select(OrgGovernanceRow.org_node_id).where(OrgGovernanceRow.head_node_id == me.id)))
    owners = sorted({me.id, *headed})
    rows = select(SecurityHoldingRow).where(SecurityHoldingRow.holder_node_id.in_(owners), SecurityHoldingRow.amount > 0).order_by(SecurityHoldingRow.id)
    for row in await session.scalars(rows):
        security = await session.get(IssuedSecurityRow, row.security_id)
        if security is None:
            continue
        whose = "you hold" if row.holder_node_id == me.id else f"your organisation {row.holder_node_id} holds"
        credit = f", {row.on_margin} on credit" if row.on_margin else ""
        found.append(f"{whose} {several(row.amount, 'unit', 'units')} of {security_line(security)}, bought at {row.bought_price}{credit}")
    return found
