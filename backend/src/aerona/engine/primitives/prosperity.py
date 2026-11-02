from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.engine.primitives.numbers import stable_roll, stochastic_round
from aerona.engine.primitives.stats import set_stats, stat
from aerona.rules.registry import Rules

PROSPERITY_KEY = "prosperity"


def prosperity_gain(rules: Rules, prosperity: float, gain: float) -> float:
    target = rules.world_effects.prosperity_target
    if gain <= 0 or prosperity <= target:
        return gain
    return gain * max(0.0, PERCENT - prosperity) / max(1, PERCENT - target)


def add_prosperity(rules: Rules, entity: EntityRow, gain: float, roll: float | None = None) -> int | None:
    current = stat(entity, PROSPERITY_KEY)
    if current is None:
        return None
    change = prosperity_gain(rules, current, gain)
    draw = roll if roll is not None else stable_roll(entity.id, f"{current}:{change:.6f}")
    updated = max(0, min(PERCENT, current + stochastic_round(change, draw)))
    set_stats(entity, prosperity=updated)
    return updated
