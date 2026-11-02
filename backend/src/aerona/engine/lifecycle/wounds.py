from enum import StrEnum

from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.context import TickContext
from aerona.engine.lifecycle.aging import is_immortal
from aerona.engine.lifecycle.mortal_death import die
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import set_stats, stat


class WoundOutcome(StrEnum):
    IMMORTAL = "immortal"
    WOUNDED = "wounded"
    DIED = "died"


async def wound(ctx: TickContext, mortal: EntityRow, damage: float, *, cause: str, killer_id: int | None = None) -> WoundOutcome | None:
    if mortal.entity_type is not EntityType.MORTAL or mortal.status is not EntityStatus.CANON:
        return None
    if await is_immortal(ctx.session, mortal):
        return WoundOutcome.IMMORTAL
    current = stat(mortal, "hp")
    base = current if current is not None else ctx.rules.world_effects.heir_hp
    remaining = max(0, round_half_up(base - damage))
    set_stats(mortal, hp=remaining)
    if remaining > 0:
        return WoundOutcome.WOUNDED
    result = await die(ctx, mortal, cause=cause, killer_id=killer_id)
    return WoundOutcome.DIED if result is not None else WoundOutcome.WOUNDED
