from aerona.constants.units import PERCENT
from aerona.domain.enums.entity import COMMUNITY_TYPES
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.primitives.numbers import clamp_int, stochastic_round
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import set_stats, stat


def reverted(prosperity: int, target: int, share_pct: int, roll: float | None = None) -> int:
    if roll is None:
        return clamp_int(prosperity + (target - prosperity) * share_pct / PERCENT, 0, PERCENT)
    return max(0, min(PERCENT, prosperity + stochastic_round((target - prosperity) * share_pct / PERCENT, roll)))


@reads("people.prosperity", "settlement.prosperity")
@writes("people.prosperity", "settlement.prosperity", "table.entities")
async def prosperity_reversion(ctx: TickContext) -> None:
    effects = ctx.rules.world_effects
    for community in await canon(ctx.session, COMMUNITY_TYPES):
        prosperity = stat(community, "prosperity")
        roll = ctx.rng(f"revert.{community.id}").random()
        if prosperity is not None and set_stats(community, prosperity=reverted(prosperity, effects.prosperity_target, effects.prosperity_reversion_pct, roll)):
            ctx.count("reverted")


PHASES = (Phase("prosperity_reversion", prosperity_reversion),)
