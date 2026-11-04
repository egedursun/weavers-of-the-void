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
    armoured_war_bonus: int = rule(10, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Armoured creature")
    burrowing_war_bonus: int = rule(3, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Burrowing creature")
    aquatic_war_bonus: int = rule(2, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Aquatic creature")
    amphibious_war_bonus: int = rule(2, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Amphibious creature")
    pack_hunter_war_bonus: int = rule(6, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Pack-hunting creature")
    ambush_predator_war_bonus: int = rule(6, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Ambush predator creature")
    regenerating_war_bonus: int = rule(5, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Regenerating creature")
    poisonous_flesh_war_bonus: int = rule(0, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Poisonous flesh creature")
    fire_breathing_war_bonus: int = rule(14, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Fire-breathing creature")
    cold_breathing_war_bonus: int = rule(12, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Frost-breathing creature")
    echolocation_war_bonus: int = rule(2, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Echolocating creature")
    camouflage_war_bonus: int = rule(2, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Camouflaged creature")
    swarm_breeder_war_bonus: int = rule(1, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Swarm-breeding creature")
    long_lived_war_bonus: int = rule(3, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Long-lived creature")
    mimic_war_bonus: int = rule(1, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Mimic creature")
    spirit_sight_war_bonus: int = rule(2, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Spirit-sighted creature")
    iron_eating_war_bonus: int = rule(2, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Iron-eating creature")
    crop_pest_war_bonus: int = rule(0, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Crop pest creature")
    plague_bearer_war_bonus: int = rule(1, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Plague-bearing creature")
    sacred_animal_war_bonus: int = rule(0, 0, 100, RuleGroup.CREATURES, "War-strength bonus of a Sacred creature")
