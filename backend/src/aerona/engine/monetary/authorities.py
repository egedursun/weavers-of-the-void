from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.economy import CurrencyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.finance import CreditProfileRow
from aerona.db.tables.monetary import MonetaryAuthorityRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.economy import CurrencyIssuer
from aerona.domain.enums.monetary import MonetaryAim
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import round_half_up

RULER_ISSUERS = frozenset({CurrencyIssuer.COMMUNITY, CurrencyIssuer.POLITY})
INSTITUTION_INDEPENDENCE = 50
FACTOR_FLOOR = 0.5
FACTOR_CAP = 2.0
MORAL_HAZARD = 1.2


@dataclass
class MonetaryTally:
    founded: int = 0
    rates_moved: int = 0
    printed: int = 0
    bent: int = 0
    resisted: int = 0
    pegs_held: int = 0
    pegs_broken: int = 0


async def authority_of(session: AsyncSession, currency_id: int | None) -> MonetaryAuthorityRow | None:
    if currency_id is None:
        return None
    return await session.scalar(select(MonetaryAuthorityRow).where(MonetaryAuthorityRow.currency_id == currency_id))


PLAIN_MONEY = "wealth"


async def money_word(session: AsyncSession, node_id: int | None) -> str:
    currency_id = await currency_for(session, node_id)
    currency = await session.get(CurrencyRow, currency_id) if currency_id is not None else None
    return currency.name if currency is not None else PLAIN_MONEY


async def currency_for(session: AsyncSession, node_id: int | None) -> int | None:
    if node_id is None:
        return None
    society = await session.get(CommunitySocietyRow, node_id)
    if society is not None and society.currency_id is not None:
        return society.currency_id
    issued = await session.scalar(select(CurrencyRow.id).where(CurrencyRow.issuer_entity_id == node_id).order_by(CurrencyRow.id).limit(1))
    if issued is not None:
        return int(issued)
    entity = await session.get(EntityRow, node_id)
    home = entity.location_id if entity is not None else None
    if home is not None and home != node_id:
        society = await session.get(CommunitySocietyRow, home)
        if society is not None and society.currency_id is not None:
            return society.currency_id
    realm = await session.scalar(
        select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == node_id).order_by(PolityMemberRow.polity_entity_id).limit(1)
    )
    if realm is not None:
        return await session.scalar(select(CurrencyRow.id).where(CurrencyRow.issuer_entity_id == realm).order_by(CurrencyRow.id).limit(1))
    return None


def rate_gap(ctx: TickContext, authority: MonetaryAuthorityRow) -> int:
    return authority.effective_rate - ctx.rules.monetary.neutral_rate


async def rate_shift(ctx: TickContext, node_id: int | None) -> int:
    authority = await authority_of(ctx.session, await currency_for(ctx.session, node_id))
    if authority is None:
        return 0
    return round_half_up(rate_gap(ctx, authority) * ctx.rules.monetary.rate_to_interest_pct / PERCENT)


async def price_factor(ctx: TickContext, currency_id: int | None) -> float:
    authority = await authority_of(ctx.session, currency_id)
    if authority is None:
        return 1.0
    return max(FACTOR_FLOOR, min(FACTOR_CAP, 1 - rate_gap(ctx, authority) * ctx.rules.monetary.price_per_rate_point_pct / PERCENT))


async def borrow_factor(ctx: TickContext, currency_id: int | None) -> float:
    authority = await authority_of(ctx.session, currency_id)
    if authority is None:
        return 1.0
    table = ctx.rules.monetary
    rate = 1 - rate_gap(ctx, authority) * table.borrow_per_rate_point_pct / PERCENT
    held_back = 1 - authority.reserve_requirement_pct * table.reserve_lending_pct / (PERCENT * PERCENT)
    hazard = MORAL_HAZARD if authority.lender_of_last_resort else 1.0
    return max(0.0, min(FACTOR_CAP, rate * held_back * hazard))


def align(authority: MonetaryAuthorityRow, currency: CurrencyRow) -> None:
    locked = authority.locked or []
    if "issuer_node_id" not in locked:
        authority.issuer_node_id = currency.issuer_entity_id
    if "coin_entity_id" not in locked:
        authority.coin_entity_id = currency.item_entity_id


async def establish(ctx: TickContext, currency: CurrencyRow) -> MonetaryAuthorityRow:
    found = await authority_of(ctx.session, currency.id)
    if found is not None:
        return found
    credit = await ctx.session.get(CreditProfileRow, currency.issuer_entity_id)
    authority = MonetaryAuthorityRow(
        currency_id=currency.id,
        holder_node_id=currency.issuer_entity_id,
        issuer_node_id=currency.issuer_entity_id,
        coin_entity_id=currency.item_entity_id,
        independence=0 if currency.issuer_kind in RULER_ISSUERS else INSTITUTION_INDEPENDENCE,
        aim=MonetaryAim.FUND_THE_STATE if currency.debased_epoch is not None else MonetaryAim.STABLE_VALUE,
        rate=ctx.rules.monetary.neutral_rate,
        effective_rate=ctx.rules.monetary.neutral_rate,
        reserves=credit.reserves if credit is not None else 0,
        founded_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(authority)
    await ctx.session.flush()
    return authority
