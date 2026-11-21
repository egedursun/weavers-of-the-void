from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import ThoughtKind, TraitEffect
from aerona.engine.mind.book import effect_of
from aerona.engine.mind.thoughts import think
from aerona.engine.mortal.profile import ensure_profile, is_held
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import MORTAL_STANDING, has_stat, shift_stat, stat
from aerona.rules.registry import Rules


async def shift(session: AsyncSession, mortal_id: int, column: str, amount: float, epoch: int) -> MortalProfileRow:
    row, _ = await ensure_profile(session, mortal_id, epoch)
    if is_held(row, column) or not amount:
        return row
    current = getattr(row, column)
    setattr(row, column, clamp_int((current or 0) + amount, 0, PERCENT))
    return row


async def add_renown(session: AsyncSession, mortal_id: int, amount: float, epoch: int, *, rules: Rules | None = None) -> MortalProfileRow:
    row = await shift(session, mortal_id, "renown", amount, epoch)
    if rules is not None and amount >= rules.thoughts.renown_thought:
        await think(session, rules, mortal_id, ThoughtKind.GAINED_RENOWN, epoch)
    return row


async def add_honour(session: AsyncSession, mortal_id: int, amount: float, epoch: int) -> MortalProfileRow:
    return await shift(session, mortal_id, "honour", amount, epoch)


async def add_infamy(session: AsyncSession, mortal_id: int, amount: float, epoch: int, *, rules: Rules | None = None) -> MortalProfileRow:
    row = await shift(session, mortal_id, "infamy", amount, epoch)
    if rules is not None and amount >= rules.thoughts.infamy_thought:
        await think(session, rules, mortal_id, ThoughtKind.WAS_SHAMED, epoch)
    return row


async def add_wealth(session: AsyncSession, mortal_id: int, amount: float, epoch: int) -> MortalProfileRow:
    return await shift(session, mortal_id, "wealth", amount, epoch)


async def add_stress(session: AsyncSession, mortal_id: int, amount: float, epoch: int) -> MortalProfileRow:
    if amount > 0:
        amount *= max(0.0, 1 - await effect_of(session, mortal_id, TraitEffect.RESILIENCE) / PERCENT)
    return await shift(session, mortal_id, "stress", amount, epoch)


def in_profile(holder: EntityRow, key: str) -> str | None:
    column = MORTAL_STANDING.get(key)
    return column if holder.entity_type is EntityType.MORTAL and column is not None and not has_stat(holder, key) else None


async def shift_standing(session: AsyncSession, holder: EntityRow, key: str, delta: float, epoch: int, *, default: int | None = None) -> None:
    column = in_profile(holder, key)
    if column is None:
        shift_stat(holder, key, delta, default)
    else:
        await shift(session, holder.id, column, delta, epoch)


async def standing_of(session: AsyncSession, holder: EntityRow, key: str) -> int | None:
    column = in_profile(holder, key)
    if column is None:
        return stat(holder, key)
    profile = await session.get(MortalProfileRow, holder.id)
    return int(getattr(profile, column)) if profile is not None else 0
