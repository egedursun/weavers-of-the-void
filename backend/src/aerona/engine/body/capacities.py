from collections.abc import Mapping
from dataclasses import dataclass

from aerona.catalog.anatomy import Anatomy
from aerona.catalog.conditions import ALERT_CAPACITIES, CONDITIONS
from aerona.catalog.life.body import FUNCTION_LEVELS
from aerona.constants.units import PERCENT
from aerona.domain.enums.body import BodyFunction, Capacity, ConditionKind, Consciousness, Handedness, NerveDamage
from aerona.engine.body.digits import hand_shares
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
    counts: Mapping[str, int]
    open_severity: int
    conditions: tuple[tuple[ConditionKind, float], ...] = ()
    presence_pct: int = PERCENT
    reader: bool = False
    afflicted: tuple[tuple[str, int], ...] = ()
    consciousness: Consciousness = Consciousness.AWAKE
    exertion: int = 0
    aid: float = 0.0
    lost_digits: tuple[str, ...] = ()
    handedness: Handedness = Handedness.RIGHT
    hearing_aid: float = 0.0
    magnifier: float = 0.0


def blend(level: float, weight: int) -> float:
    return 1 - weight / PERCENT * (1 - max(0.0, min(1.0, level)))


def pain_of(rules: CapacityRules, open_severity: int) -> int:
    return max(0, min(rules.pain_cap, open_severity * rules.pain_per_severity))


def condition_penalty(rules: CapacityRules, kind: ConditionKind) -> dict[Capacity, int]:
    return CONDITIONS[kind].penalty(rules)


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
    levels = function_levels(
        table, state.anatomy, state.wounds, state.counts, rules.injury.venom_paralysis_at, afflicted=state.afflicted, share=rules.body.tentacle_share
    )
    grip = weapon_grasp(table, state.anatomy, state.wounds, state.counts, hands=hand_shares(state.lost_digits), handedness=state.handedness)
    pain = pain_of(table, state.open_severity) / PERCENT
    hurt = 1 - pain * table.pain_weight_pct / PERCENT
    if any(wound.nerve is NerveDamage.SENSORY for wound in state.wounds):
        levels[F.FINE_MANIPULATION] *= 1 - rules.tissues.numbness_pct / PERCENT
    stride = max(levels[F.LOCOMOTION], levels[F.FLIGHT], state.aid)
    horn = levels[F.HORN] if state.anatomy.with_function(F.HORN) else 1.0
    tail = levels[F.TAIL] if state.anatomy.with_function(F.TAIL) else 1.0
    reading = max(levels[F.SIGHT], table.reader_restore_pct / PERCENT) if state.reader else levels[F.SIGHT]
    levels[F.HEARING] = max(levels[F.HEARING], state.hearing_aid)
    values: dict[Capacity, float] = {}
    values[C.MELEE] = (
        stats.strength
        * blend(grip, table.melee_grasp)
        * blend(stride, table.melee_locomotion)
        * blend(levels[F.VITAL], table.melee_vital)
        * blend(levels[F.SIGHT], table.melee_sight)
        * blend(horn, table.melee_horn)
        * hurt
    )
    values[C.MISSILE] = (
        stats.agility
        * blend(levels[F.SIGHT], table.missile_sight)
        * blend(levels[F.FINE_MANIPULATION], table.missile_fine)
        * blend(grip, table.missile_grasp)
        * hurt
    )
    values[C.COMMAND] = (
        (stats.intellect + stats.charisma)
        / 2
        * blend(levels[F.SPEECH], table.command_speech)
        * blend(levels[F.SIGHT], table.command_sight)
        * blend(levels[F.HEARING], table.command_hearing)
        * blend(levels[F.COGNITION], table.command_cognition)
    )
    values[C.CRAFT] = (
        stats.intellect
        * blend(grip, table.craft_grasp)
        * blend(levels[F.FINE_MANIPULATION], table.craft_fine)
        * blend(levels[F.SIGHT], table.craft_sight)
        * blend(levels[F.COGNITION], table.craft_cognition)
        * hurt
        * (1 + state.magnifier)
    )
    values[C.SCHOLARSHIP] = stats.intellect * blend(reading, table.scholarship_sight) * blend(levels[F.COGNITION], table.scholarship_cognition)
    values[C.PRESENCE] = (
        stats.charisma
        * blend(levels[F.PRESENCE], table.presence_face)
        * blend(levels[F.SPEECH], table.presence_speech)
        * blend(horn, table.presence_horn)
        * state.presence_pct
        / PERCENT
    )
    values[C.MOBILITY] = (
        stats.endurance
        * blend(stride, table.mobility_locomotion)
        * blend(levels[F.BREATH], table.mobility_breath)
        * blend(levels[F.VITAL], table.mobility_vital)
        * blend(tail, table.mobility_tail)
        * hurt
    )
    values[C.ENDURANCE] = (
        stats.endurance
        * blend(levels[F.BREATH], table.mobility_breath)
        * blend(levels[F.VITAL], table.mobility_vital)
        * blend(stride, table.mobility_locomotion)
        * hurt
    )
    values[C.PERCEPTION] = (
        PERCENT * perception_factor(table, round(levels[F.HEARING] * PERCENT), round(reading * PERCENT)) * blend(levels[F.COGNITION], table.command_cognition)
    )
    values[C.STEALTH] = values[C.PERCEPTION] * blend(stride, table.stealth_stride) * state.presence_pct / PERCENT
    values[C.LABOUR] = (
        stats.strength * blend(grip, table.labour_grasp) * blend(stride, table.mobility_locomotion) * blend(levels[F.BREATH], table.mobility_breath) * hurt
    )
    values[C.FERTILITY] = (
        PERCENT
        * blend(levels[F.REPRODUCTION], table.fertility_reproduction)
        * blend(levels[F.VITAL], table.fertility_vital)
        * age_curve(table, stats.age, stats.lifespan)
    )
    for kind, severity in state.conditions:
        for capacity, penalty in condition_penalty(table, kind).items():
            values[capacity] *= 1 - penalty * severity / table.condition_full_severity / PERCENT
    alert = alertness(rules, state.consciousness)
    for capacity in ALERT_CAPACITIES:
        values[capacity] *= alert
    if state.exertion >= rules.tissues.exhausted_at:
        values[C.MELEE] *= rules.tissues.exhausted_pct / PERCENT
        values[C.MISSILE] *= rules.tissues.exhausted_pct / PERCENT
    return {capacity: max(0, round(value)) for capacity, value in values.items()}


def alertness(rules: Rules, state: Consciousness) -> float:
    table = rules.tissues
    return {
        Consciousness.AWAKE: 1.0,
        Consciousness.NAUSEOUS: table.nauseous_pct / PERCENT,
        Consciousness.DIZZY: table.dizzy_pct / PERCENT,
        Consciousness.UNCONSCIOUS: 0.0,
    }[state]


def function_percents(rules: Rules, state: BodyState) -> dict[BodyFunction, int]:
    levels = function_levels(rules.capacities, state.anatomy, state.wounds, state.counts, rules.injury.venom_paralysis_at)
    return {function: max(0, min(PERCENT, round(levels[function] * PERCENT))) for function in FUNCTION_LEVELS}


def perception_factor(rules: CapacityRules, hearing: int, sight: int) -> float:
    return blend(hearing / PERCENT, rules.perception_hearing) * blend(sight / PERCENT, rules.perception_sight)
