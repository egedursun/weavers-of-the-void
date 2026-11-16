from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.living import LivingLineTraitRow
from aerona.domain.enums.living import LineTrait


async def traits_of(session: AsyncSession, line_id: int | None) -> dict[LineTrait, int]:
    if line_id is None:
        return {}
    rows = await session.execute(select(LivingLineTraitRow.trait, LivingLineTraitRow.strength).where(LivingLineTraitRow.line_id == line_id))
    found: dict[LineTrait, int] = {}
    for trait, strength in rows.all():
        found[trait] = found.get(trait, 0) + strength
    return found


def scaled(value: int, strength: int) -> int:
    return max(0, value * (PERCENT + strength) // PERCENT)


def eased(value: int, strength: int) -> int:
    return max(0, value * (PERCENT - max(0, min(PERCENT, strength))) // PERCENT)
