from aerona.domain.enums.foreign_god import ForeignGodPowerEffect
from aerona.domain.enums.son import Stat
from aerona.prompts.environment import string_template
from aerona.rules.registry import Rules

F = ForeignGodPowerEffect

ABOVE_NEUTRAL = "each point above neutral ({{ rules.foreign_gods.stat_neutral }}) gives {{ '%g' | format(rate / 100) }}"

FOREIGN_STAT_EFFECTS: dict[Stat, tuple[str, str]] = {
    Stat.STRENGTH: (
        "War power: (Strength + Will) / 2, weighted {{ rules.foreign_gods.war_stat_share_pct }}% in war (the rest is its general power).",
        "war_stat_share_pct",
    ),
    Stat.WILL: ("Half of war power; resistance to sons' alliance, threat and bargaining rolls: " + ABOVE_NEUTRAL + " roll reduction.", "talk_will"),
    Stat.ENDURANCE: ("Wakes sooner when defeated: " + ABOVE_NEUTRAL + " ages shorter.", "wake_endurance"),
    Stat.AGILITY: ("When hostile, attempts to steal worshippers or tear down temples: " + ABOVE_NEUTRAL + " points (%) added.", "attack_agility"),
    Stat.WISDOM: ("When friendly, chance to help its worshippers: " + ABOVE_NEUTRAL + " points (%) added.", "help_wisdom"),
    Stat.CUNNING: ("Chance to turn the sons' worshippers to itself: " + ABOVE_NEUTRAL + " points (%) added.", "steal_cunning"),
    Stat.CHARISMA: ("Chance to draw unclaimed communities of its world: " + ABOVE_NEUTRAL + " points (%) added.", "attract_charisma"),
    Stat.CREATIVITY: ("When friendly, prosperity it adds to its worshippers: " + ABOVE_NEUTRAL + " prosperity added.", "prosperity_creativity"),
    Stat.MIGHT: ("Threshold to grow stronger from worshippers' faith: " + ABOVE_NEUTRAL + " faith lower.", "growth_faith_might"),
}

FOREIGN_POWER_EFFECTS: dict[ForeignGodPowerEffect, str] = {
    F.SHIELD: "In war, +{{ rules.foreign_gods.power_shield }} to its power.",
    F.CALLER: "Chance to draw unclaimed communities +{{ rules.foreign_gods.power_caller }}%.",
    F.THIEF: "Chance to steal the sons' worshippers +{{ rules.foreign_gods.power_thief }}%.",
    F.DESTROYER: "When hostile, attack chance +{{ rules.foreign_gods.power_destroyer }}%.",
    F.FERTILE: "When friendly, prosperity added to worshippers x{{ '%g' | format(rules.foreign_gods.power_bountiful / 100) }}.",
    F.REVIVING: "When defeated, wake time drops to {{ rules.foreign_gods.power_reviving }}%.",
    F.DEATHLESS: "Even in a crushing defeat it does not die; it is only laid low.",
    F.SHARP_TONGUED: "The roll of a son who talks with it -{{ rules.foreign_gods.power_sharp_tongue }}.",
}


def foreign_stat_effect(stat: Stat, rules: Rules) -> str:
    source, rate_key = FOREIGN_STAT_EFFECTS[stat]
    return string_template(source).render(rules=rules, rate=getattr(rules.foreign_gods, rate_key)).strip()


def foreign_power_effect(effect: ForeignGodPowerEffect, rules: Rules) -> str:
    return string_template(FOREIGN_POWER_EFFECTS[effect]).render(rules=rules).strip()
