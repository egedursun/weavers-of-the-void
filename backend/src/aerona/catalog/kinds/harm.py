from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.body import DamageType, HarmCause, InjuryKind


@dataclass(frozen=True)
class HarmCauseSpec:
    heat_rule: str
    pierce: InjuryKind
    mix: tuple[tuple[DamageType, str], ...]


D = DamageType
H = HarmCause
HARM_CAUSES: Mapping[HarmCause, HarmCauseSpec] = total(
    HarmCause,
    {
        H.BATTLE: HarmCauseSpec(
            "fire_heat", InjuryKind.PUNCTURE, ((D.CUT, "battle_cut"), (D.PIERCE, "battle_pierce"), (D.BLUNT, "battle_blunt"), (D.FIRE, "battle_fire"))
        ),
        H.DUEL: HarmCauseSpec("fire_heat", InjuryKind.PUNCTURE, ((D.CUT, "duel_cut"), (D.PIERCE, "duel_pierce"), (D.BLUNT, "duel_blunt"))),
        H.PUNISHMENT: HarmCauseSpec("fire_heat", InjuryKind.PUNCTURE, ((D.CUT, "punishment_cut"), (D.BLUNT, "punishment_blunt"), (D.FIRE, "punishment_fire"))),
        H.TORTURE: HarmCauseSpec("fire_heat", InjuryKind.PUNCTURE, ((D.CUT, "torture_cut"), (D.BLUNT, "torture_blunt"), (D.FIRE, "torture_fire"))),
        H.ACCIDENT: HarmCauseSpec("fire_heat", InjuryKind.PUNCTURE, ((D.BLUNT, "accident_blunt"), (D.CUT, "accident_cut"), (D.FIRE, "accident_fire"))),
        H.MONSTER: HarmCauseSpec(
            "dragon_heat", InjuryKind.BITE, ((D.CUT, "monster_claw"), (D.PIERCE, "monster_bite"), (D.BLUNT, "monster_crush"), (D.VENOM, "monster_venom"))
        ),
        H.DISASTER: HarmCauseSpec(
            "magma_heat", InjuryKind.PUNCTURE, ((D.BLUNT, "disaster_blunt"), (D.FIRE, "disaster_fire"), (D.COLD, "disaster_cold"), (D.CUT, "disaster_cut"))
        ),
        H.CURSE: HarmCauseSpec("fire_heat", InjuryKind.PUNCTURE, ((D.MAGIC, "curse_magic"), (D.VOID, "curse_void"))),
        H.MAGIC_BACKLASH: HarmCauseSpec("fire_heat", InjuryKind.PUNCTURE, ((D.MAGIC, "backlash_magic"), (D.FIRE, "backlash_fire"), (D.VOID, "backlash_void"))),
        H.GOD: HarmCauseSpec("fire_heat", InjuryKind.PUNCTURE, ((D.HOLY, "god_holy"), (D.FIRE, "god_fire"), (D.BLUNT, "god_blunt"))),
        H.POISON: HarmCauseSpec("fire_heat", InjuryKind.PUNCTURE, ((D.VENOM, "poison_venom"),)),
        H.QUEST: HarmCauseSpec(
            "fire_heat", InjuryKind.PUNCTURE, ((D.CUT, "quest_cut"), (D.BLUNT, "quest_blunt"), (D.COLD, "quest_cold"), (D.PIERCE, "quest_pierce"))
        ),
        H.ESCAPE: HarmCauseSpec("fire_heat", InjuryKind.PUNCTURE, ((D.BLUNT, "escape_blunt"), (D.CUT, "escape_cut"))),
        H.SACRIFICE: HarmCauseSpec("fire_heat", InjuryKind.PUNCTURE, ((D.CUT, "sacrifice_cut"), (D.MAGIC, "sacrifice_magic"))),
        H.AGE: HarmCauseSpec("fire_heat", InjuryKind.PUNCTURE, ((D.BLUNT, "age_blunt"),)),
        H.PLAYER: HarmCauseSpec("fire_heat", InjuryKind.PUNCTURE, ((D.CUT, "player_cut"), (D.BLUNT, "player_blunt"), (D.PIERCE, "player_pierce"))),
        H.EXPOSURE: HarmCauseSpec("fire_heat", InjuryKind.PUNCTURE, ((D.COLD, "exposure_cold"), (D.FIRE, "exposure_heat"))),
        H.RITUAL: HarmCauseSpec("fire_heat", InjuryKind.PUNCTURE, ((D.CUT, "ritual_cut"), (D.FIRE, "ritual_fire"))),
        H.BOMBARDMENT: HarmCauseSpec(
            "fire_heat", InjuryKind.PUNCTURE, ((D.EXPLOSIVE, "bombardment_explosive"), (D.BLUNT, "bombardment_blunt"), (D.FIRE, "bombardment_fire"))
        ),
        H.INDUSTRIAL: HarmCauseSpec(
            "fire_heat",
            InjuryKind.PUNCTURE,
            (
                (D.BLUNT, "industrial_blunt"),
                (D.CUT, "industrial_cut"),
                (D.FIRE, "industrial_fire"),
                (D.CHEMICAL, "industrial_chemical"),
                (D.ELECTRIC, "industrial_electric"),
            ),
        ),
        H.CRASH: HarmCauseSpec("fire_heat", InjuryKind.PUNCTURE, ((D.BLUNT, "crash_blunt"), (D.CUT, "crash_cut"), (D.FIRE, "crash_fire"))),
        H.RADIATION: HarmCauseSpec("fire_heat", InjuryKind.PUNCTURE, ((D.RADIATION, "radiation_radiation"),)),
        H.DECOMPRESSION: HarmCauseSpec("fire_heat", InjuryKind.PUNCTURE, ((D.COLD, "decompression_cold"), (D.BLUNT, "decompression_blunt"))),
        H.EXPERIMENT: HarmCauseSpec(
            "fire_heat",
            InjuryKind.PUNCTURE,
            (
                (D.CHEMICAL, "experiment_chemical"),
                (D.RADIATION, "experiment_radiation"),
                (D.ELECTRIC, "experiment_electric"),
                (D.PSYCHIC, "experiment_psychic"),
            ),
        ),
        H.POWER: HarmCauseSpec("fire_heat", InjuryKind.PUNCTURE, ((D.PSYCHIC, "power_psychic"), (D.BLUNT, "power_blunt"))),
    },
)
