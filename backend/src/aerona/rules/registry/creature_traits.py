from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class CreatureTraitsRules:
    flying_war_bonus: int = rule(8, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Flying creature")
    venomous_war_bonus: int = rule(10, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Venomous creature")
    soul_eater_war_bonus: int = rule(4, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Soul-eating creature")
    radiant_war_bonus: int = rule(0, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Light-radiating creature")
    fissiparous_war_bonus: int = rule(2, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a creature that multiplies by splitting")
    hive_mind_war_bonus: int = rule(6, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Swarm-minded creature")
    stoneskin_war_bonus: int = rule(12, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Stone-skinned creature")
    time_rewinder_war_bonus: int = rule(0, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Time-rewinding creature")
    shapeshifter_war_bonus: int = rule(3, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Shapeshifting creature")
    mind_reader_war_bonus: int = rule(8, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Mind-reading creature")
