from sqlalchemy import or_, select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.economy import CurrencyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.monetary import MonetaryAuthorityRow
from aerona.domain.enums.monetary import MonetaryAim
from aerona.engine.monetary.authorities import currency_for


async def authority_line(scope: Scope, authority: MonetaryAuthorityRow, currency: CurrencyRow) -> str:
    holder = await named(scope, authority.holder_node_id) if authority.holder_node_id is not None else "no one"
    peg = ""
    if authority.aim is MonetaryAim.PEG:
        target = await scope.session.get(CurrencyRow, authority.peg_currency_id) if authority.peg_currency_id is not None else None
        peg = f", held to {target.name if target is not None else spoken(authority.peg_good) if authority.peg_good is not None else 'nothing'}"
    lender = ", lends to failing banks" if authority.lender_of_last_resort else ""
    return (
        f"{currency.name} (currency {currency.id}) is issued by {holder} (authority {authority.id}), aiming at {spoken(authority.aim)}{peg}: "
        f"rate {authority.rate}, felt now {authority.effective_rate}, independence {authority.independence}, reserves {authority.reserves}, "
        f"reserve requirement {authority.reserve_requirement_pct}, trust {currency.trust}{lender}"
    )


async def mortal_money_policy_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    home_currency = await currency_for(session, me.location_id)
    query = select(MonetaryAuthorityRow).where(or_(MonetaryAuthorityRow.holder_node_id == me.id, MonetaryAuthorityRow.currency_id == home_currency))
    found: list[str] = []
    for authority in await session.scalars(query.order_by(MonetaryAuthorityRow.id)):
        currency = await session.get(CurrencyRow, authority.currency_id)
        if currency is not None:
            found.append(await authority_line(scope, authority, currency))
    return found
