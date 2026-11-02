from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class ForeignGodsRules:
    stat_base: int = rule(35, 1, 100, RuleGroup.FOREIGN_GODS, "Base of each stat of a new foreign god")
    stat_die: int = rule(45, 0, 100, RuleGroup.FOREIGN_GODS, "Die added to each stat of a new foreign god")
    stat_neutral: int = rule(50, 0, 100, RuleGroup.FOREIGN_GODS, "Neutral stat: above this has a positive effect, below a negative one")
    war_stat_share_pct: int = rule(50, 0, 100, RuleGroup.FOREIGN_GODS, "Share of (Strength + Will) / 2 in war strength (%); the rest is general power")
    talk_will: int = rule(
        30, 0, 500, RuleGroup.FOREIGN_GODS, "Will's resistance in talking with a son: (Will \u2212 neutral) \u00d7 this / 100 is subtracted from the die"
    )
    attract_charisma: int = rule(
        20,
        0,
        500,
        RuleGroup.FOREIGN_GODS,
        "Charisma contribution to the chance of attracting worshippers: (Charisma \u2212 neutral) \u00d7 this / 100 points (%)",
    )
    steal_cunning: int = rule(
        20, 0, 500, RuleGroup.FOREIGN_GODS, "Cunning contribution to the chance of stealing worshippers: (Cunning \u2212 neutral) \u00d7 this / 100 points (%)"
    )
    attack_agility: int = rule(
        20, 0, 500, RuleGroup.FOREIGN_GODS, "Agility contribution to the chance of a hostile action: (Agility \u2212 neutral) \u00d7 this / 100 points (%)"
    )
    help_wisdom: int = rule(
        20, 0, 500, RuleGroup.FOREIGN_GODS, "Wisdom contribution to the chance of friendly help: (Wisdom \u2212 neutral) \u00d7 this / 100 points (%)"
    )
    prosperity_creativity: int = rule(
        10,
        0,
        500,
        RuleGroup.FOREIGN_GODS,
        "Creativity effect on the friendly prosperity contribution: (Creativity \u2212 neutral) \u00d7 this / 100 prosperity",
    )
    wake_endurance: int = rule(
        10,
        0,
        500,
        RuleGroup.FOREIGN_GODS,
        "Endurance effect on the wake-up time after defeat: shortened by (Endurance \u2212 neutral) \u00d7 this / 100 epochs",
    )
    growth_faith_might: int = rule(
        20, 0, 500, RuleGroup.FOREIGN_GODS, "Might effect on the strengthening threshold: (Might \u2212 neutral) \u00d7 this / 100 faith lower"
    )
    powers_count: int = rule(2, 0, 20, RuleGroup.FOREIGN_GODS, "Number of powers given to a foreign god when deepened")
    power_shield: int = rule(15, 0, 500, RuleGroup.FOREIGN_GODS, "Shield power: added to war strength")
    power_caller: int = rule(15, 0, 100, RuleGroup.FOREIGN_GODS, "Caller power: added to the chance of attracting worshippers (%)")
    power_thief: int = rule(15, 0, 100, RuleGroup.FOREIGN_GODS, "Worshipper-thief power: added to the chance of stealing worshippers (%)")
    power_destroyer: int = rule(15, 0, 100, RuleGroup.FOREIGN_GODS, "Destroyer power: added to the chance of a hostile action (%)")
    power_bountiful: int = rule(200, 100, 10000, RuleGroup.FOREIGN_GODS, "Bountiful power: multiplier of the friendly prosperity contribution (%)")
    power_reviving: int = rule(50, 1, 100, RuleGroup.FOREIGN_GODS, "Reviving power: percentage of the wake-up time after defeat")
    power_sharp_tongue: int = rule(15, 0, 500, RuleGroup.FOREIGN_GODS, "Sharp-tongued power: subtracted from the die of a son talking with it")
    action_full_faith: int = rule(
        10,
        1,
        100000,
        RuleGroup.FOREIGN_GODS,
        "A foreign god's attacks, thefts and help reach full chance at this faith (below it they scale with faith; a faithless god does nothing)",
    )
    action_full_power: int = rule(
        50, 1, 100, RuleGroup.FOREIGN_GODS, "A foreign god's actions, attraction included, reach full chance at this power (below it they scale with power)"
    )
