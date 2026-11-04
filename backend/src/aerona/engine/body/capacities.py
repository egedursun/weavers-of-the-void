from collections.abc import Iterable
from dataclasses import dataclass

from aerona.catalog.anatomy import Anatomy
from aerona.constants.units import PERCENT
from aerona.domain.enums.body import BodyFunction, Capacity, ConditionKind
from aerona.engine.body.functions import Wound, function_levels, weapon_grasp
from aerona.rules.registry import Rules
from aerona.rules.registry.body import CapacityRules

F = BodyFunction
C = Capacity


@dataclass(frozen=True)
class BearerStats:
    strength: float
    agility: float
    intellect: float
    charisma: float
    endurance: float
    age: int | None = None
    lifespan: int | None = None


@dataclass(frozen=True)
class BodyState:
    anatomy: Anatomy
    wounds: tuple[Wound, ...]
    fingers: int
    open_severity: int
    conditions: tuple[tuple[ConditionKind, float], ...] = ()
    presence_pct: int = PERCENT
    reader: bool = False
    afflicted: tuple[tuple[str, int], ...] = ()


def blend(level: float, weight: int) -> float:
    return 1 - weight / PERCENT * (1 - max(0.0, min(1.0, level)))


def pain_of(rules: CapacityRules, open_severity: int) -> int:
    return max(0, min(rules.pain_cap, open_severity * rules.pain_per_severity))


def condition_penalty(rules: CapacityRules, kind: ConditionKind) -> dict[Capacity, int]:
    table: dict[ConditionKind, dict[Capacity, int]] = {
        ConditionKind.CHRONIC_ILLNESS: {C.MOBILITY: rules.illness_mobility, C.MELEE: rules.illness_melee, C.FERTILITY: rules.illness_fertility},
        ConditionKind.PARANOIA: {C.COMMAND: rules.paranoia_command, C.PRESENCE: rules.paranoia_presence},
        ConditionKind.VISIONS: {C.SCHOLARSHIP: rules.visions_scholarship, C.PRESENCE: -rules.visions_presence},
        ConditionKind.RAGE: {C.MELEE: -rules.rage_melee, C.COMMAND: rules.rage_command, C.CRAFT: rules.rage_craft},
        ConditionKind.MELANCHOLY: {C.COMMAND: rules.melancholy_command, C.CRAFT: rules.melancholy_craft, C.PRESENCE: rules.melancholy_presence},
        ConditionKind.ADDICTION: {C.CRAFT: rules.addiction_craft, C.SCHOLARSHIP: rules.addiction_scholarship, C.PRESENCE: rules.addiction_presence},
        ConditionKind.AGE_BLINDNESS: {C.MISSILE: rules.blindness_missile, C.SCHOLARSHIP: rules.blindness_scholarship, C.CRAFT: rules.blindness_craft},
        ConditionKind.AGE_DEAFNESS: {C.COMMAND: rules.deafness_command},
        ConditionKind.WITHERED_LIMB: {C.MELEE: rules.withered_melee, C.CRAFT: rules.withered_craft},
        ConditionKind.ENDLESS_HUNGER: {C.MOBILITY: rules.hunger_mobility, C.PRESENCE: rules.hunger_presence},
        ConditionKind.POSSESSION: {C.COMMAND: rules.possession_command, C.PRESENCE: rules.possession_presence, C.MELEE: -rules.possession_melee},
        ConditionKind.VOID_TAINT: {C.SCHOLARSHIP: rules.void_scholarship, C.PRESENCE: rules.void_presence},
        ConditionKind.CHOSEN_MARK: {C.PRESENCE: -rules.chosen_presence, C.MELEE: -rules.chosen_melee},
        ConditionKind.DIVINE_BRAND: {C.PRESENCE: -rules.brand_presence},
    }
    return table[kind]


def age_curve(rules: CapacityRules, age: int | None, lifespan: int | None) -> float:
    if age is None or not lifespan:
        return 1.0
    share = age * PERCENT / max(1, lifespan)
    if share < rules.fertility_start_pct:
        return 0.0
    if share <= rules.fertility_prime_end_pct:
        return 1.0
    if share >= rules.fertility_end_pct:
        return 0.0
    span = max(1, rules.fertility_end_pct - rules.fertility_prime_end_pct)
    return 1 - (share - rules.fertility_prime_end_pct) / span


def capacities(rules: Rules, stats: BearerStats, state: BodyState) -> dict[Capacity, int]:
    table = rules.capacities
    levels = function_levels(table, state.anatomy, state.wounds, state.fingers, rules.injury.venom_paralysis_at, afflicted=state.afflicted)
    grip = weapon_grasp(table, state.anatomy, state.wounds, state.fingers)
    pain = pain_of(table, state.open_severity) / PERCENT
    hurt = 1 - pain * table.pain_weight_pct / PERCENT
    stride = max(levels[F.LOCOMOTION], levels[F.FLIGHT])
    horn = levels[F.HORN] if state.anatomy.with_function(F.HORN) else 1.0
    tail = levels[F.TAIL] if state.anatomy.with_function(F.TAIL) else 1.0
    reading = max(levels[F.SIGHT], table.reader_restore_pct / PERCENT) if state.reader else levels[F.SIGHT]
    values: dict[Capacity, float] = {
        C.MELEE: stats.strength
        * blend(grip, table.melee_grasp)
        * blend(stride, table.melee_locomotion)
        * blend(levels[F.VITAL], table.melee_vital)
        * blend(levels[F.SIGHT], table.melee_sight)
        * blend(horn, table.melee_horn)
        * hurt,
        C.MISSILE: stats.agility
        * blend(levels[F.SIGHT], table.missile_sight)
        * blend(levels[F.FINE_MANIPULATION], table.missile_fine)
        * blend(grip, table.missile_grasp)
        * hurt,
        C.COMMAND: (stats.intellect + stats.charisma)
        / 2
        * blend(levels[F.SPEECH], table.command_speech)
        * blend(levels[F.SIGHT], table.command_sight)
        * blend(levels[F.HEARING], table.command_hearing)
        * blend(levels[F.COGNITION], table.command_cognition),
        C.CRAFT: stats.intellect
        * blend(grip, table.craft_grasp)
        * blend(levels[F.FINE_MANIPULATION], table.craft_fine)
        * blend(levels[F.SIGHT], table.craft_sight)
        * blend(levels[F.COGNITION], table.craft_cognition)
        * hurt,
        C.SCHOLARSHIP: stats.intellect * blend(reading, table.scholarship_sight) * blend(levels[F.COGNITION], table.scholarship_cognition),
        C.PRESENCE: stats.charisma
        * blend(levels[F.PRESENCE], table.presence_face)
        * blend(levels[F.SPEECH], table.presence_speech)
        * blend(horn, table.presence_horn)
        * state.presence_pct
        / PERCENT,
        C.MOBILITY: stats.endurance
        * blend(stride, table.mobility_locomotion)
        * blend(levels[F.BREATH], table.mobility_breath)
        * blend(levels[F.VITAL], table.mobility_vital)
        * blend(tail, table.mobility_tail)
        * hurt,
        C.FERTILITY: PERCENT
        * blend(levels[F.REPRODUCTION], table.fertility_reproduction)
        * blend(levels[F.VITAL], table.fertility_vital)
        * age_curve(table, stats.age, stats.lifespan),
    }
    for kind, severity in state.conditions:
        for capacity, penalty in condition_penalty(table, kind).items():
            values[capacity] *= 1 - penalty * severity / table.condition_full_severity / PERCENT
    return {capacity: max(0, round(value)) for capacity, value in values.items()}


FUNCTION_LEVELS = (F.VITAL, F.COGNITION, F.HEARING, F.SIGHT, F.VENOM, F.HORN, F.TAIL)


def function_percents(rules: Rules, state: BodyState) -> dict[BodyFunction, int]:
    levels = function_levels(rules.capacities, state.anatomy, state.wounds, state.fingers, rules.injury.venom_paralysis_at)
    return {function: max(0, min(PERCENT, round(levels[function] * PERCENT))) for function in FUNCTION_LEVELS}


def perception_factor(rules: CapacityRules, hearing: int, sight: int) -> float:
    return blend(hearing / PERCENT, rules.perception_hearing) * blend(sight / PERCENT, rules.perception_sight)


def healthy(rules: Rules, stats: BearerStats, anatomy: Anatomy, fingers: int) -> dict[Capacity, int]:
    return capacities(rules, stats, BodyState(anatomy, (), fingers, 0))


def summary(values: dict[Capacity, int], keys: Iterable[Capacity] = tuple(Capacity)) -> dict[str, int]:
    return {capacity.value: values[capacity] for capacity in keys}
