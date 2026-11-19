from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class NativeFaithRules:
    turn_chance: int = rule(4, 0, 100, RuleGroup.FOREIGN_GODS, "Chance per epoch a native community open to its old god turns to it (%)")
    weak_piety: int = rule(40, 0, 100, RuleGroup.FOREIGN_GODS, "A native community below this piety is open to the old god")
    disaster_bonus: int = rule(10, 0, 100, RuleGroup.FOREIGN_GODS, "Added to the turning chance of a native struck by a disaster or plague this epoch (%)")
    patronless_bonus: int = rule(
        15, 0, 100, RuleGroup.FOREIGN_GODS, "Added to the turning chance of a native whose patron sleeps, died, rebelled or never was (%)"
    )
    sleeping_pull_pct: int = rule(50, 0, 100, RuleGroup.FOREIGN_GODS, "Pull of a sleeping or defeated old god compared with an awake one (%)")
    syncretic_share: int = rule(65, 0, 100, RuleGroup.FOREIGN_GODS, "Chance a turning native keeps its patron and worships both gods (%)")
    turn_cap: int = rule(
        1, 0, 10000, RuleGroup.FOREIGN_GODS, "Base of the most communities turning to one old god per epoch, grown by the communities of its world"
    )
    cap_community_divisor: int = rule(
        5,
        0,
        10000,
        RuleGroup.FOREIGN_GODS,
        "Communities per extra community turning to or returning from the old gods in an epoch (0: the caps stay at their base)",
    )
    return_chance: int = rule(4, 0, 100, RuleGroup.FOREIGN_GODS, "Chance per epoch a worshipper of an old god returns to the pantheon (%)")
    return_defeated_mult_pct: int = rule(300, 0, 10000, RuleGroup.FOREIGN_GODS, "Return chance multiplier when the old god sleeps or is defeated (%)")
    return_cap: int = rule(
        2,
        0,
        10000,
        RuleGroup.FOREIGN_GODS,
        "Base of the most communities returning from old gods to the pantheon per epoch, grown by the number of their believers",
    )
    power_floor: int = rule(20, 0, 100, RuleGroup.FOREIGN_GODS, "Power an old god without worshippers sinks to")
    power_faith_divisor: int = rule(2, 1, 1000, RuleGroup.FOREIGN_GODS, "Target power of an old god: floor + faith divided by this")
    power_step: int = rule(2, 0, 100, RuleGroup.FOREIGN_GODS, "Most an old god's power changes per epoch")
    syncretic_weight_pct: int = rule(50, 0, 100, RuleGroup.FOREIGN_GODS, "Faith a syncretic worshipper gives the old god compared with a full worshipper (%)")
    stance_peace: int = rule(1, 0, 100, RuleGroup.FOREIGN_GODS, "Stance gained for every trade or alliance between its worshippers and the pantheon's")
    stance_war: int = rule(2, 0, 100, RuleGroup.FOREIGN_GODS, "Stance lost for every enmity between its worshippers and the pantheon's")
    stance_syncretic: int = rule(1, 0, 100, RuleGroup.FOREIGN_GODS, "Stance gained for every community worshipping it alongside a son")
    stance_loss: int = rule(3, 0, 100, RuleGroup.FOREIGN_GODS, "Stance lost when a worshipper returns to the pantheon")
    stance_step: int = rule(5, 0, 100, RuleGroup.FOREIGN_GODS, "Most an old god's stance changes from events per epoch")
