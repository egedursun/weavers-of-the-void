from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.rules.registry import Rules

TREASURY_LOCK = "treasury"


async def realm_purse(session: AsyncSession, payer: EntityRow) -> PolityProfileRow | None:
    own = await session.get(PolityProfileRow, payer.id)
    if own is not None:
        return own
    polity_id = await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == payer.id).limit(1))
    return await session.get(PolityProfileRow, polity_id) if polity_id is not None else None


def wealth_points(rules: Rules, amount: int) -> int:
    return max(1, round_half_up(amount / max(1, rules.taxation.wealth_per_treasury))) if amount > 0 else 0


async def coin_of(session: AsyncSession, rules: Rules, payer: EntityRow) -> int:
    realm = await realm_purse(session, payer)
    treasury = realm.treasury if realm is not None and TREASURY_LOCK not in realm.locked else 0
    return treasury + (stat(payer, "wealth") or 0) * max(1, rules.taxation.wealth_per_treasury)


async def take_coin(session: AsyncSession, rules: Rules, payer: EntityRow, amount: int) -> bool:
    if amount <= 0:
        return True
    realm = await realm_purse(session, payer)
    if realm is not None and TREASURY_LOCK not in realm.locked and realm.treasury >= amount:
        realm.treasury -= amount
        return True
    points = wealth_points(rules, amount)
    if (stat(payer, "wealth") or 0) < points:
        return False
    shift_stat(payer, "wealth", -points)
    return True


def give_coin(rules: Rules, payee: EntityRow, amount: int) -> None:
    if amount > 0 and stat(payee, "wealth") is not None:
        shift_stat(payee, "wealth", wealth_points(rules, amount))


async def receive_coin(session: AsyncSession, rules: Rules, payee: EntityRow, amount: int) -> None:
    if amount <= 0:
        return
    realm = await realm_purse(session, payee)
    if realm is not None and TREASURY_LOCK not in realm.locked:
        realm.treasury += amount
        return
    give_coin(rules, payee, amount)
