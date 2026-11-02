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
    )
}


def trait_war_bonus(rules: Rules, trait: CreatureTrait) -> int:
    return CREATURE_TRAITS[trait].war_bonus(rules)
