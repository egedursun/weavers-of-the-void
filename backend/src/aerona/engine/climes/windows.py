from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.climes import LaunchWindowRow
from aerona.domain.enums.travel import TravelMethod
from aerona.rules.registry import Rules

PHYSICAL = frozenset({TravelMethod.LIGHT_SAIL, TravelMethod.SLINGSHOT_ORBIT, TravelMethod.COSMIC_MOUNT, TravelMethod.VOID_ARK})


def pair(first: int, second: int) -> tuple[int, int]:
    return (first, second) if first < second else (second, first)


def opens(row: LaunchWindowRow, epoch: int) -> bool:
    return (epoch + row.offset) % max(1, row.synodic) == 0


async def window_delay(session: AsyncSession, rules: Rules, method: TravelMethod, ends: tuple[int, int], epoch: int) -> int:
    if method not in PHYSICAL:
        return 0
    row = await session.get(LaunchWindowRow, pair(*ends))
    if row is None or row.open or opens(row, epoch):
        return 0
    return rules.launch_windows.closed_epochs
