from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.mind import ThoughtKind
from aerona.engine.mind.thoughts import think
from aerona.engine.mortal.profile import ensure_profile, is_held
from aerona.engine.primitives.numbers import clamp_int
from aerona.rules.registry import Rules

STANDING_COLUMNS = ("wealth", "renown", "honour", "infamy", "legitimacy", "stress", "health", "education")


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
    return await shift(session, mortal_id, "stress", amount, epoch)


async def renown_of(session: AsyncSession, mortal_id: int) -> int:
    row = await session.get(MortalProfileRow, mortal_id)
    return row.renown if row is not None else 0
