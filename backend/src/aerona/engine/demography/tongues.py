from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.engine.body.customs import people_of
from aerona.engine.lore.language import barrier, tongues_of
from aerona.rules.registry import Rules


async def trade_tongue(session: AsyncSession, community_id: int) -> int | None:
    entity = await session.get(EntityRow, community_id)
    people = await people_of(session, entity) if entity is not None else None
    culture = await session.get(PeopleCultureRow, people.id) if people is not None else None
    return culture.trade_language_id if culture is not None else None


def shares_tongue(first_trade: int | None, second_trade: int | None, first_tongues: set[int], second_tongues: set[int]) -> bool:
    if first_trade is not None and (first_trade == second_trade or first_trade in second_tongues):
        return True
    return second_trade is not None and second_trade in first_tongues


async def shared_trade_tongue(session: AsyncSession, first: int, second: int) -> bool:
    ours, theirs = await trade_tongue(session, first), await trade_tongue(session, second)
    if ours is None and theirs is None:
        return False
    return shares_tongue(ours, theirs, await tongues_of(session, first), await tongues_of(session, second))


async def trade_barrier(session: AsyncSession, rules: Rules, first: int, second: int, epoch: int) -> float:
    if await shared_trade_tongue(session, first, second):
        return rules.customs.trade_tongue_pct / PERCENT
    return await barrier(session, rules, first, second, epoch)


async def tongue_link(session: AsyncSession, rules: Rules, first: int, second: int) -> float:
    return rules.customs.trade_tongue_diffusion_pct / PERCENT if await shared_trade_tongue(session, first, second) else 1.0
