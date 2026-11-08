from collections.abc import Callable
from dataclasses import dataclass

from aerona.domain.enums.son import ExistenceBand, ExistenceMode, Passion, Stat, StatGroup
from aerona.rules.registry import Rules

PERCENT = 100


@dataclass(frozen=True)
class StatSpec:
    stat: Stat
    label: str
    abbreviation: str
    group: StatGroup
    describe: Callable[[Rules], str]


@dataclass(frozen=True)
class LabelledKey[K]:
    key: K
    label: str
    meaning: str


STATS: dict[Stat, StatSpec] = {
    spec.stat: spec
    for spec in (
        StatSpec(Stat.STRENGTH, "Strength", "STR", StatGroup.BODY, lambda rules: "Weight in strength duels; strengthens the armies that worship this god."),
        StatSpec(
            Stat.ENDURANCE,
            "Endurance",
            "END",
            StatGroup.BODY,
            lambda rules: (
                f"Max HP = {rules.core_rules.max_hp_base} + {rules.core_rules.max_hp_per_endurance / PERCENT:g} x endurance; heals faster each epoch."
            ),
        ),
        StatSpec(Stat.AGILITY, "Agility", "AGI", StatGroup.BODY, lambda rules: "Initiative: who acts first in the epoch."),
        StatSpec(Stat.WISDOM, "Wisdom", "WIS", StatGroup.MIND, lambda rules: "Wisdom duels; sees the world more widely; harvests resources more efficiently."),
        StatSpec(Stat.CUNNING, "Cunning", "CUN", StatGroup.MIND, lambda rules: "Cunning duels, initiative and inciting war."),
        StatSpec(Stat.WILL, "Will", "WIL", StatGroup.MIND, lambda rules: "Resists punishments and curses; with low loyalty they disobey orders."),
        StatSpec(
            Stat.CREATIVITY,
            "Creativity",
            "CRE",
            StatGroup.SPIRIT,
            lambda rules: f"Lowers creation cost, by up to {rules.core_rules.creativity_discount_pct}% at full creativity.",
        ),
        StatSpec(Stat.CHARISMA, "Charisma", "CHA", StatGroup.SPIRIT, lambda rules: "Cult growth, stealing worshippers through dreams, sway among siblings."),
        StatSpec(
            Stat.MIGHT,
            "Might",
            "MIG",
            StatGroup.SPIRIT,
            lambda rules: f"Max essence = {rules.core_rules.max_essence_base} + {rules.core_rules.max_essence_per_might / PERCENT:g} x might.",
        ),
    )
}


PASSIONS: dict[Passion, LabelledKey[Passion]] = {
    item.key: item
    for item in (
        LabelledKey(Passion.LOYALTY, "Loyalty", "Tendency to obey the Creator's orders."),
        LabelledKey(Passion.AMBITION, "Ambition", "Pursuit of power and faith; a high value challenges siblings."),
        LabelledKey(Passion.WRATH, "Wrath", "Tendency toward destructive creations and hostility."),
        LabelledKey(Passion.MERCY, "Mercy", "Compassion toward mortals and siblings."),
    )
}


EXISTENCE_MODES: dict[ExistenceMode, str] = {
    ExistenceMode.CONCRETE: "Concrete",
    ExistenceMode.SEMI_CONCRETE: "Semi-concrete",
    ExistenceMode.CONCEPTUAL: "Conceptual",
    ExistenceMode.REFLECTION: "Reflection",
    ExistenceMode.SCATTERED: "Scattered",
}

EXISTENCE_BAND_LABELS: dict[ExistenceBand, str] = {
    ExistenceBand.RADIANT: "Radiant",
    ExistenceBand.SOLID: "Solid",
    ExistenceBand.FADED: "Faded",
    ExistenceBand.BEING_FORGOTTEN: "Being forgotten",
}


def existence_band(rules: Rules, existence: int) -> ExistenceBand:
    core = rules.core_rules
    if existence >= core.existence_radiant:
        return ExistenceBand.RADIANT
    if existence >= core.existence_solid:
        return ExistenceBand.SOLID
    if existence >= core.existence_faded:
        return ExistenceBand.FADED
    return ExistenceBand.BEING_FORGOTTEN


def max_hp(rules: Rules, endurance: int) -> int:
    core = rules.core_rules
    return round(core.max_hp_base + core.max_hp_per_endurance / PERCENT * endurance)


def max_essence(rules: Rules, might: int | None) -> int:
    core = rules.core_rules
    value = core.default_might if might is None else might
    return round(core.max_essence_base + core.max_essence_per_might / PERCENT * value)


def existence_band_effect(rules: Rules, band: ExistenceBand) -> str:
    if band is ExistenceBand.RADIANT:
        return f"+{rules.world_epoch_transition.radiant_essence_bonus} essence every epoch."
    if band is ExistenceBand.SOLID:
        return "Normal."
    if band is ExistenceBand.FADED:
        return f"{rules.core_rules.faded_action_loss} action point less; starts forgetting its body."
    return "Cannot act. Needs a worshipper or the Creator's blessing."
