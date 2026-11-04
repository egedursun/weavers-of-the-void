from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.culture import LanguageRegisterRow
from aerona.domain.enums.culture import LanguageRegister
from aerona.engine.lore.language import chosen_trade_tongue, register_barrier, tongues_of
from aerona.rules.registry import Rules


async def trade_tongue(session: AsyncSession, community_id: int) -> int | None:
    row = await session.get(LanguageRegisterRow, (community_id, LanguageRegister.TRADE))
    return row.language_entity_id if row is not None else await chosen_trade_tongue(session, community_id)


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
    return await register_barrier(session, rules, first, second, epoch, ours=LanguageRegister.TRADE, theirs=LanguageRegister.TRADE)


async def tongue_link(session: AsyncSession, rules: Rules, first: int, second: int) -> float:
    return rules.customs.trade_tongue_diffusion_pct / PERCENT if await shared_trade_tongue(session, first, second) else 1.0
