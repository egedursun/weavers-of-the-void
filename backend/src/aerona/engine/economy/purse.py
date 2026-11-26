from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultDoctrineRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import has_stat, shift_stat, stat, stat_or
from aerona.rules.registry import Rules

TREASURY_LOCK = "treasury"
WEALTH = "wealth"


async def realm_purse(session: AsyncSession, payer: EntityRow) -> PolityProfileRow | None:
    own = await session.get(PolityProfileRow, payer.id)
    if own is not None:
        return own
    polity_id = await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == payer.id).limit(1))
    return await session.get(PolityProfileRow, polity_id) if polity_id is not None else None


def held_coin(treasury: int) -> int:
    return max(0, treasury)


def wealth_points(rules: Rules, amount: int) -> int:
    return max(1, round_half_up(amount / max(1, rules.taxation.wealth_per_treasury))) if amount > 0 else 0


async def purse_of(session: AsyncSession, holder: EntityRow) -> MortalProfileRow | None:
    if holder.entity_type is not EntityType.MORTAL:
        return None
    return await session.get(MortalProfileRow, holder.id)


async def points_of(session: AsyncSession, holder: EntityRow) -> int:
    if holder.entity_type is EntityType.MORTAL:
        profile = await purse_of(session, holder)
        return profile.wealth if profile is not None else 0
    return stat(holder, "wealth") or 0


async def shift_points(session: AsyncSession, holder: EntityRow, points: int) -> None:
    if holder.entity_type is not EntityType.MORTAL:
        shift_stat(holder, "wealth", points, default=0)
        return
    profile = await purse_of(session, holder)
    if profile is None:
        profile = MortalProfileRow(entity_id=holder.id, locked=[])
        session.add(profile)
    if WEALTH not in (profile.locked or []):
        profile.wealth = clamp_int((profile.wealth or 0) + points, 0, PERCENT)


async def coin_of(session: AsyncSession, rules: Rules, payer: EntityRow) -> int:
    realm = await realm_purse(session, payer)
    treasury = realm.treasury if realm is not None and TREASURY_LOCK not in realm.locked else 0
    return treasury + await points_of(session, payer) * max(1, rules.taxation.wealth_per_treasury)


async def take_coin(session: AsyncSession, rules: Rules, payer: EntityRow, amount: int) -> bool:
    if amount <= 0:
        return True
    realm = await realm_purse(session, payer)
    if realm is not None and TREASURY_LOCK not in realm.locked and realm.treasury >= amount:
        realm.treasury -= amount
        return True
    points = wealth_points(rules, amount)
    profile = await purse_of(session, payer)
    if await points_of(session, payer) < points or (profile is not None and WEALTH in (profile.locked or [])):
        return False
    await shift_points(session, payer, -points)
    return True


def riches_of(holder: EntityRow) -> int:
    return stat_or(holder, "wealth", stat(holder, "prosperity") or 0)


def holds_wealth(holder: EntityRow) -> bool:
    return holder.entity_type is EntityType.MORTAL or has_stat(holder, "wealth")


async def give_coin(session: AsyncSession, rules: Rules, payee: EntityRow, amount: int) -> None:
    if amount <= 0:
        return
    if holds_wealth(payee):
        await shift_points(session, payee, wealth_points(rules, amount))
        return
    doctrine = await session.get(CultDoctrineRow, payee.id)
    if doctrine is not None and TREASURY_LOCK not in doctrine.locked:
        doctrine.treasury += amount
        return
    realm = await realm_purse(session, payee)
    if realm is not None and TREASURY_LOCK not in realm.locked:
        realm.treasury += amount
        return
    place = await session.get(EntityRow, payee.location_id) if payee.location_id is not None else None
    if place is not None:
        await give_coin(session, rules, place, amount)


async def receive_coin(session: AsyncSession, rules: Rules, payee: EntityRow, amount: int) -> None:
    if amount <= 0:
        return
    realm = await realm_purse(session, payee)
    if realm is not None and TREASURY_LOCK not in realm.locked:
        realm.treasury += amount
        return
    await give_coin(session, rules, payee, amount)
