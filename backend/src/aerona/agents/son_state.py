from aerona.agents.context.powers import unlocked
from aerona.catalog.rarities import build_rarity_table
from aerona.core.random import SeededRandom
from aerona.db.tables.sons import SonPowerRow, SonRow
from aerona.domain.enums.limits import MAX_STARS
from aerona.domain.enums.son import PowerEffect
from aerona.rules.registry import Rules

INITIATIVE_DIE_FACTOR = 2
INITIATIVE_CUNNING_DIVISOR = 2


def has_power(rules: Rules, son: SonRow, powers: list[SonPowerRow], effect: PowerEffect) -> bool:
    return any(power.effect is effect and unlocked(rules, son, power) for power in powers)


def action_points(rules: Rules, son: SonRow, powers: list[SonPowerRow]) -> int:
    core = rules.core_rules
    points = build_rarity_table(rules)[son.rarity].action_points
    if has_power(rules, son, powers, PowerEffect.TIRELESS):
        points += core.tireless_extra_action
    if son.stars >= MAX_STARS:
        points += core.max_star_extra_action
    if son.existence < core.existence_solid:
        points -= core.faded_action_loss
    floor = 0 if son.existence < core.existence_faded else core.min_actions
    return max(floor, points)


def initiative(rules: Rules, son: SonRow, rng: SeededRandom) -> float:
    return son.agility + son.cunning / INITIATIVE_CUNNING_DIVISOR + rng.die(rules.core_rules.initiative_die) * INITIATIVE_DIE_FACTOR


def turn_order(ordered: list[tuple[SonRow, float]]) -> list[tuple[SonRow, float]]:
    pinned = sorted((item for item in ordered if item[0].turn_rank is not None), key=lambda item: (item[0].turn_rank or 0, -item[1]))
    rest = sorted((item for item in ordered if item[0].turn_rank is None), key=lambda item: -item[1])
    return pinned + rest


def max_turns(rules: Rules, son: SonRow) -> int:
    return build_rarity_table(rules)[son.rarity].max_turns
