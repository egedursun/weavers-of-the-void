import math
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.cosmos import CosmosRow
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class DoomStep:
    before: int
    after: int
    scaled: float


def doom_threshold(rules: Rules) -> int:
    return max(1, rules.balance.apocalypse_threshold)


def step_doom(rules: Rules, cosmos: CosmosRow, amount: float, *, scaled: bool = True) -> DoomStep:
    change = amount * rules.balance.apocalypse_speed / PERCENT if scaled else amount
    before = cosmos.doom_clock
    raw = before + (cosmos.doom_fraction or 0.0) + change
    whole = math.trunc(raw)
    after = max(0, min(doom_threshold(rules), whole))
    cosmos.doom_clock = after
    cosmos.doom_fraction = raw - whole if after == whole else 0.0
    return DoomStep(before, after, change)


async def advance_doom(session: AsyncSession, rules: Rules, amount: float) -> int:
    cosmos = await CosmosRepository(session).require_cosmos()
    step_doom(rules, cosmos, amount)
    await session.flush()
    return cosmos.doom_clock


async def doom_share(session: AsyncSession, rules: Rules) -> float:
    cosmos = await CosmosRepository(session).require_cosmos()
    return cosmos.doom_clock / doom_threshold(rules)
