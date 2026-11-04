from collections.abc import Callable
from dataclasses import dataclass

from aerona.domain.enums.society import CreatureTrait
from aerona.rules.registry import Rules

C = CreatureTrait


@dataclass(frozen=True)
class CreatureTraitSpec:
    trait: CreatureTrait
    label: str
    effect: str
    war_bonus: Callable[[Rules], int]


CREATURE_TRAITS: dict[CreatureTrait, CreatureTraitSpec] = {
    spec.trait: spec
    for spec in (
        CreatureTraitSpec(C.FLYING, "Flying", "Migrates easily and raids reach far.", lambda rules: rules.creature_traits.flying_war_bonus),
        CreatureTraitSpec(
            C.VENOMOUS, "Venomous", "Grievous wounds in hunt and war; kills heroes easily.", lambda rules: rules.creature_traits.venomous_war_bonus
        ),
        CreatureTraitSpec(
            C.SOUL_EATER,
            "Soul-eating",
            "Devours spirits in its region and gnaws the sanity of those nearby.",
            lambda rules: rules.creature_traits.soul_eater_war_bonus,
        ),
        CreatureTraitSpec(
            C.RADIANT,
            "Light-radiating",
            "Lowers its region's danger, raises fertility, keeps Outer Beings away.",
            lambda rules: rules.creature_traits.radiant_war_bonus,
        ),
        CreatureTraitSpec(
            C.FISSIPAROUS,
            "Multiplies by splitting",
            "Spreads if unchecked: migrates and invades more often.",
            lambda rules: rules.creature_traits.fissiparous_war_bonus,
        ),
        CreatureTraitSpec(C.HIVE_MIND, "Swarm-minded", "Weak alone, clever together; hard to hunt.", lambda rules: rules.creature_traits.hive_mind_war_bonus),
        CreatureTraitSpec(C.STONESKIN, "Stone-skinned", "Heroes' weapons barely bite.", lambda rules: rules.creature_traits.stoneskin_war_bonus),
        CreatureTraitSpec(
            C.TIME_REWINDER, "Time-rewinding", "Returns once in the epoch it is killed.", lambda rules: rules.creature_traits.time_rewinder_war_bonus
        ),
        CreatureTraitSpec(
            C.SHAPESHIFTER, "Shapeshifting", "Blends among peoples; espionage and discord.", lambda rules: rules.creature_traits.shapeshifter_war_bonus
        ),
        CreatureTraitSpec(
            C.MIND_READER,
            "Mind-reading",
            "Knows heroes' moves in advance and lowers the sanity of those nearby.",
            lambda rules: rules.creature_traits.mind_reader_war_bonus,
        ),
        CreatureTraitSpec(C.ARMOURED, "Armoured", "Hides and plates turn hunters and predators aside.", lambda rules: rules.creature_traits.armoured_war_bonus),
        CreatureTraitSpec(
            C.BURROWING, "Burrowing", "Lives below the ground and outlasts the clearing of its land.", lambda rules: rules.creature_traits.burrowing_war_bonus
        ),
        CreatureTraitSpec(C.AQUATIC, "Aquatic", "Thrives in seas, rivers and marshes.", lambda rules: rules.creature_traits.aquatic_war_bonus),
        CreatureTraitSpec(C.AMPHIBIOUS, "Amphibious", "At home on shore and in water alike.", lambda rules: rules.creature_traits.amphibious_war_bonus),
        CreatureTraitSpec(
            C.PACK_HUNTER, "Pack-hunting", "Hunts in packs that bleed prey herds fast.", lambda rules: rules.creature_traits.pack_hunter_war_bonus
        ),
        CreatureTraitSpec(
            C.AMBUSH_PREDATOR,
            "Ambush predator",
            "Strikes from cover; its raids on herds cost more.",
            lambda rules: rules.creature_traits.ambush_predator_war_bonus,
        ),
        CreatureTraitSpec(C.REGENERATING, "Regenerating", "Shrugs off sickness and the hunt.", lambda rules: rules.creature_traits.regenerating_war_bonus),
        CreatureTraitSpec(
            C.POISONOUS_FLESH,
            "Poisonous flesh",
            "Cannot be eaten: neither people nor predators hunt it.",
            lambda rules: rules.creature_traits.poisonous_flesh_war_bonus,
        ),
        CreatureTraitSpec(C.FIRE_BREATHING, "Fire-breathing", "Its raids burn what they reach.", lambda rules: rules.creature_traits.fire_breathing_war_bonus),
        CreatureTraitSpec(
            C.COLD_BREATHING, "Frost-breathing", "Its raids freeze what they reach.", lambda rules: rules.creature_traits.cold_breathing_war_bonus
        ),
        CreatureTraitSpec(
            C.ECHOLOCATION, "Echolocating", "Hunts by sound in the dark: a keen nocturnal hunter.", lambda rules: rules.creature_traits.echolocation_war_bonus
        ),
        CreatureTraitSpec(C.CAMOUFLAGE, "Camouflaged", "Hard to find for hunter and predator alike.", lambda rules: rules.creature_traits.camouflage_war_bonus),
        CreatureTraitSpec(
            C.SWARM_BREEDER, "Swarm-breeding", "Breeds in swarms and recovers fast.", lambda rules: rules.creature_traits.swarm_breeder_war_bonus
        ),
        CreatureTraitSpec(
            C.LONG_LIVED, "Long-lived", "Lives long and breeds slowly; its numbers swing little.", lambda rules: rules.creature_traits.long_lived_war_bonus
        ),
        CreatureTraitSpec(C.MIMIC, "Mimic", "Looks like something dangerous, and is left alone.", lambda rules: rules.creature_traits.mimic_war_bonus),
        CreatureTraitSpec(
            C.SPIRIT_SIGHT, "Spirit-sighted", "Sees the dead; restless spirits quieten near it.", lambda rules: rules.creature_traits.spirit_sight_war_bonus
        ),
        CreatureTraitSpec(
            C.IRON_EATING, "Iron-eating", "Eats ore and metal: a pest of mines and smithies.", lambda rules: rules.creature_traits.iron_eating_war_bonus
        ),
        CreatureTraitSpec(C.CROP_PEST, "Crop pest", "Strips fields and cuts the harvest.", lambda rules: rules.creature_traits.crop_pest_war_bonus),
        CreatureTraitSpec(
            C.PLAGUE_BEARER, "Plague-bearing", "Carries sickness wherever it ranges.", lambda rules: rules.creature_traits.plague_bearer_war_bonus
        ),
        CreatureTraitSpec(C.SACRED_ANIMAL, "Sacred", "Held holy: the faithful will not hunt it.", lambda rules: rules.creature_traits.sacred_animal_war_bonus),
    )
}


def trait_war_bonus(rules: Rules, trait: CreatureTrait) -> int:
    return CREATURE_TRAITS[trait].war_bonus(rules)
