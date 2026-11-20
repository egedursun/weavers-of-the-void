from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from aerona.core.grammar import several
from aerona.domain.enums.son import PowerEffect
from aerona.rules.registry import Rules

PERCENT = 100


class PowerParam(StrEnum):
    ENTITY_TYPE = "entity_type"
    STAT = "stat"


@dataclass(frozen=True)
class PowerSpec:
    effect: PowerEffect
    name: str
    param: PowerParam | None
    describe: Callable[[Rules], str]


def _discount(rules: Rules) -> int:
    return PERCENT - rules.core_rules.cheap_power_cost_pct


POWERS: dict[PowerEffect, PowerSpec] = {
    spec.effect: spec
    for spec in (
        PowerSpec(
            PowerEffect.CHEAP_CREATION,
            "Master Creator",
            PowerParam.ENTITY_TYPE,
            lambda rules: f"Creations of the chosen type are {_discount(rules)}% cheaper.",
        ),
        PowerSpec(
            PowerEffect.DUEL_MASTER,
            "Duel Master",
            PowerParam.STAT,
            lambda rules: f"+{rules.son_tools.challenge_power_bonus} in duels that use the chosen stat.",
        ),
        PowerSpec(
            PowerEffect.ESSENCE_SPRING,
            "Essence Spring",
            None,
            lambda rules: f"+{rules.world_epoch_transition.essence_spring_bonus} essence every epoch.",
        ),
        PowerSpec(
            PowerEffect.WORSHIPPED,
            "Worshipped",
            None,
            lambda rules: f"Faith x{rules.faith.multiplier_power_pct / PERCENT:g}.",
        ),
        PowerSpec(
            PowerEffect.TIRELESS,
            "Tireless",
            None,
            lambda rules: f"+{rules.core_rules.tireless_extra_action} action point every epoch.",
        ),
        PowerSpec(
            PowerEffect.UNTOUCHABLE,
            "Untouchable",
            None,
            lambda rules: (
                f"Duels against this son -{rules.son_tools.challenge_untouchable}; "
                f"curses against their worshippers resist by {rules.son_tools.curse_untouchable_resist}."
            ),
        ),
        PowerSpec(
            PowerEffect.DREAM_SENDING,
            "Dream Whisper",
            None,
            lambda rules: f"+{rules.son_tools.dream_sending_bonus_pct}% success when sending dreams.",
        ),
        PowerSpec(
            PowerEffect.WAR_LEADER,
            "War leader",
            None,
            lambda rules: f"Contribution to the war strength of armies that worship this son x{rules.world_war_strength.war_leader_mult}.",
        ),
        PowerSpec(
            PowerEffect.HARVESTER,
            "Harvester",
            None,
            lambda rules: f"Essence from harvesting resources x{rules.son_tools.harvest_power_mult}.",
        ),
        PowerSpec(
            PowerEffect.SEER,
            "Seer",
            None,
            lambda rules: f"Prophecies are {_discount(rules)}% cheaper; fulfilled-prophecy rewards x{rules.fate.seer_power_mult}.",
        ),
        PowerSpec(
            PowerEffect.REVIVING,
            "Reviving",
            None,
            lambda rules: f"When their HP runs out they sleep only {several(rules.son_tools.reviving_sleep_epochs, 'epoch', 'epochs')}.",
        ),
        PowerSpec(
            PowerEffect.BOUNTY_GIVER,
            "Bounty-giver",
            None,
            lambda rules: f"Peoples and settlements that worship this son grow x{rules.world_epoch_transition.bounty_power_growth_mult} as fast.",
        ),
        PowerSpec(
            PowerEffect.CURSER,
            "Curser",
            None,
            lambda rules: f"Curses cost {rules.son_tools.curser_cost_pct}% and strike at {rules.son_tools.curser_severity_pct}% severity.",
        ),
    )
}


def power_description(rules: Rules, effect: PowerEffect) -> str:
    return POWERS[effect].describe(rules)


def power_unlock_levels(rules: Rules) -> tuple[int, ...]:
    levels = rules.power_unlock_levels
    return (levels.power_1_unlock_level, levels.power_2_unlock_level, levels.power_3_unlock_level)


def unlocked_power_slots(rules: Rules, level: int) -> tuple[int, ...]:
    return tuple(slot for slot, required in enumerate(power_unlock_levels(rules)) if level >= required)
