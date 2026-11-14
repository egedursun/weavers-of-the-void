from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.crafts import PublicClockRow
from aerona.rules.registry import Rules


async def precision_of(session: AsyncSession, town_id: int | None) -> int:
    row = await session.get(PublicClockRow, town_id) if town_id is not None else None
    return row.precision if row is not None else 0


async def clock_output(session: AsyncSession, rules: Rules, town_id: int) -> float:
    return 1 + await precision_of(session, town_id) * rules.clocks.output_pct / PERCENT / PERCENT


async def clock_muster(session: AsyncSession, rules: Rules, town_id: int) -> float:
    return 1 + await precision_of(session, town_id) * rules.clocks.command_pct / PERCENT / PERCENT


async def clock_navigation(session: AsyncSession, rules: Rules, ends: tuple[int, int]) -> float:
    best = max([await precision_of(session, end) for end in ends])
    return 1 - best * rules.clocks.navigation_pct / PERCENT / PERCENT
