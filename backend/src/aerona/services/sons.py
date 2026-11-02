from dataclasses import dataclass

from aerona.catalog.powers import unlocked_power_slots
from aerona.catalog.rarities import build_rarity_table
from aerona.catalog.stats import existence_band
from aerona.core.random import SeededRandom
from aerona.db.tables.sons import SonPowerRow, SonRow
from aerona.domain.enums.limits import MAX_STARS, PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.son import ExistenceBand, PowerEffect, Stat
from aerona.domain.models.stats import StatBlock
from aerona.engine.gods.progress import StarRequirement, clamp_stat, star_requirement
from aerona.rules.registry import Rules

STRENGTH_COUNT = 2


def can_act(rules: Rules, son: SonRow) -> bool:
    return son.existence >= rules.core_rules.existence_faded


def band(rules: Rules, son: SonRow) -> ExistenceBand:
    return existence_band(rules, son.existence)


def unlocked_powers(rules: Rules, son: SonRow, powers: list[SonPowerRow]) -> list[SonPowerRow]:
    slots = set(unlocked_power_slots(rules, son.level))
    return [power for power in powers if power.slot in slots]


def has_power(rules: Rules, son: SonRow, powers: list[SonPowerRow], effect: PowerEffect, parameter: str | None = None) -> bool:
    for power in unlocked_powers(rules, son, powers):
        if power.effect is not effect:
            continue
        value = power.param_entity_type or power.param_stat
        if parameter is None or (value is not None and value.value == parameter):
            return True
    return False


def gross_action_points(rules: Rules, son: SonRow, powers: list[SonPowerRow]) -> int:
    core = rules.core_rules
    points = build_rarity_table(rules)[son.rarity].action_points
    if has_power(rules, son, powers, PowerEffect.TIRELESS):
        points += core.tireless_extra_action
    if son.stars >= MAX_STARS:
        points += core.max_star_extra_action
    return max(core.min_actions, points)


def action_points(rules: Rules, son: SonRow, powers: list[SonPowerRow]) -> int:
    core = rules.core_rules
    points = gross_action_points(rules, son, powers)
    if not can_act(rules, son):
        return 0
    if son.existence < core.existence_solid:
        return max(core.min_actions, points - core.faded_action_loss)
    return points


def band_action_loss(rules: Rules, son: SonRow, powers: list[SonPowerRow]) -> int:
    return gross_action_points(rules, son, powers) - action_points(rules, son, powers)


def existence_target(rules: Rules, *, faith: int, fame: int, anchor_alive: bool | None, has_worshippers: bool) -> int:
    core = rules.core_rules
    target = core.existence_base
    target += min(core.existence_faith_cap, faith // core.existence_faith_divisor)
    target += min(core.existence_renown_cap, fame // core.existence_renown_divisor)
    if anchor_alive is True:
        target += core.existence_anchor_bonus
    elif anchor_alive is False:
        target -= core.existence_anchorless_penalty
    if not has_worshippers:
        target -= core.existence_no_worshipper_penalty
    return max(PERCENT_MIN, min(PERCENT_MAX, target))


def summoned_stats(rules: Rules, rarity: Rarity, rng: SeededRandom) -> StatBlock:
    profile = build_rarity_table(rules)[rarity]
    values = {stat: rng.integer(profile.stat_min, profile.stat_max) for stat in Stat}
    order = rng.shuffled(list(Stat))
    for stat in order[:STRENGTH_COUNT]:
        values[stat] = clamp_stat(values[stat] + rules.core_rules.strength_bonus)
    weakness = order[STRENGTH_COUNT]
    values[weakness] = clamp_stat(values[weakness] - rules.core_rules.weakness_penalty)
    return StatBlock.from_mapping(values)


@dataclass(frozen=True)
class AscensionRequirement:
    target: Rarity
    stars: int
    level: int
    fame: int
    essence: int


def next_star(rules: Rules, son: SonRow) -> StarRequirement | None:
    if son.stars >= MAX_STARS:
        return None
    return star_requirement(rules, son.stars + 1)


def ascension(rules: Rules, son: SonRow) -> AscensionRequirement | None:
    target = son.rarity.next()
    if target is None:
        return None
    return AscensionRequirement(target, MAX_STARS, rules.ascension.level, rules.ascension.renown, rules.ascension.essence_cost)
