from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.economy import CurrencyRow, MarketPriceRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.monetary import RATE_MAX, MonetaryAuthorityRow
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.monetary import MonetaryAim
from aerona.engine.context import TickContext
from aerona.engine.economy.good_kinds import good_book
from aerona.engine.monetary.authorities import MonetaryTally
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.record import record


async def peg_gap(ctx: TickContext, authority: MonetaryAuthorityRow, currency: CurrencyRow, issuer: EntityRow | None) -> int | None:
    if authority.peg_currency_id is not None:
        target = await ctx.session.get(CurrencyRow, authority.peg_currency_id)
        return target.trust - currency.trust if target is not None else None
    if authority.peg_good is None:
        return None
    market = issuer.id if issuer is not None else None
    price = await ctx.session.scalar(
        select(MarketPriceRow.price)
        .where(MarketPriceRow.market_entity_id == market, MarketPriceRow.commodity == authority.peg_good)
        .order_by(MarketPriceRow.epoch.desc())
        .limit(1)
    )
    if price is None:
        return 0
    base = max(1, (await good_book(ctx.session)).base_price(authority.peg_good))
    return clamp_int(round_half_up((base - price) * PERCENT / base), -PERCENT, PERCENT)


async def break_peg(ctx: TickContext, authority: MonetaryAuthorityRow, currency: CurrencyRow, tally: MonetaryTally) -> None:
    table = ctx.rules.monetary
    locked = authority.locked or []
    if "aim" not in locked:
        authority.aim = MonetaryAim.STABLE_VALUE
    if "rate" not in locked:
        authority.rate = clamp_int(authority.rate + table.peg_shock_rate, 0, RATE_MAX)
    if not currency.held:
        currency.trust = clamp_int(currency.trust - table.peg_shock_trust, 0, PERCENT)
    authority.peg_broken_epoch, authority.peg_reserves = ctx.epoch, 0
    tally.pegs_broken += 1
    await record(
        ctx,
        "money.peg_broken",
        roles={IncidentRole.ACTOR: authority.holder_node_id, IncidentRole.SUBJECT: currency.item_entity_id},
        facts={"currency": currency.name, "reserves": authority.reserves, "rate": authority.rate, "trust": currency.trust},
    )


async def defend_peg(ctx: TickContext, authority: MonetaryAuthorityRow, currency: CurrencyRow, issuer: EntityRow | None, tally: MonetaryTally) -> None:
    table = ctx.rules.monetary
    gap = await peg_gap(ctx, authority, currency, issuer)
    if gap is None:
        return
    if not authority.peg_reserves:
        authority.peg_reserves = authority.reserves
    cost = abs(gap) * table.peg_defence_cost
    if "reserves" not in (authority.locked or []):
        authority.reserves = max(0, authority.reserves - cost)
    if authority.reserves < round_half_up(authority.peg_reserves * table.peg_reserve_floor_pct / PERCENT) or (cost and not authority.reserves):
        await break_peg(ctx, authority, currency, tally)
        return
    if authority.peg_currency_id is not None and not currency.held:
        currency.trust = clamp_int(currency.trust + gap, 0, PERCENT)
    if cost:
        tally.pegs_held += 1
        await record(
            ctx,
            "money.peg_held",
            roles={IncidentRole.ACTOR: authority.holder_node_id, IncidentRole.SUBJECT: currency.item_entity_id},
            facts={"currency": currency.name, "spent": cost, "reserves": authority.reserves},
        )
