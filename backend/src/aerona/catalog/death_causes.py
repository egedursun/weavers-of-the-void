from collections.abc import Mapping
from dataclasses import dataclass

from aerona.catalog.kinds.harm import HARM_DEATHS
from aerona.core.total import total
from aerona.domain.enums.body import DamageType, HarmCause
from aerona.domain.enums.mortal import DeathCause

D = DeathCause


@dataclass(frozen=True)
class DeathCauseSpec:
    label: str
    violent: bool = False
    natural: bool = False
    combat: bool = False
    judged: bool = False
    offered: bool = False
    own_hand: bool = False
    uncanny: bool = False
    damage: DamageType | None = None
    loose: bool = False


DEATH_CAUSES: Mapping[DeathCause, DeathCauseSpec] = total(
    DeathCause,
    {
        D.OLD_AGE: DeathCauseSpec("Old age", natural=True),
        D.WOUNDS: DeathCauseSpec("Wounds", loose=True),
        D.BATTLE: DeathCauseSpec("Battle", violent=True, combat=True),
        D.DUEL: DeathCauseSpec("Duel", violent=True, combat=True),
        D.EXECUTION: DeathCauseSpec("Execution", violent=True, judged=True),
        D.MURDER: DeathCauseSpec("Murder", violent=True),
        D.MONSTER: DeathCauseSpec("A beast", combat=True),
        D.DISEASE: DeathCauseSpec("Disease"),
        D.CHILDBIRTH: DeathCauseSpec("Childbirth"),
        D.FAMINE: DeathCauseSpec("Famine"),
        D.ACCIDENT: DeathCauseSpec("Accident", loose=True),
        D.DISASTER: DeathCauseSpec("Disaster", loose=True),
        D.EXPOSURE: DeathCauseSpec("Exposure", loose=True),
        D.CURSE: DeathCauseSpec("Curse", uncanny=True),
        D.MAGIC: DeathCauseSpec("Magic", uncanny=True),
        D.DIVINE: DeathCauseSpec("A god's hand", offered=True),
        D.POISON: DeathCauseSpec("Poison"),
        D.SACRIFICE: DeathCauseSpec("Sacrifice", violent=True, offered=True),
        D.HARDSHIP: DeathCauseSpec("Hardship"),
        D.DESPAIR: DeathCauseSpec("Despair", own_hand=True),
        D.UNKNOWN: DeathCauseSpec("Unknown", loose=True),
        D.INDUSTRIAL: DeathCauseSpec("Industry"),
        D.CRASH: DeathCauseSpec("Crash"),
        D.RADIATION: DeathCauseSpec("Radiation"),
        D.DECOMPRESSION: DeathCauseSpec("Loss of air pressure"),
        D.EXPERIMENT: DeathCauseSpec("Experiment"),
        D.BOMBARDMENT: DeathCauseSpec("Bombardment", violent=True),
        D.DROWNING: DeathCauseSpec("Drowning", damage=DamageType.ASPHYXIA),
        D.SPORT: DeathCauseSpec("Sport"),
        D.ANIMAL: DeathCauseSpec("An animal", loose=True),
        D.CROWD: DeathCauseSpec("A crush of people", violent=True, loose=True),
        D.MEDICAL: DeathCauseSpec("Treatment gone wrong"),
        D.SOUL_LOSS: DeathCauseSpec("Loss of the soul", uncanny=True),
    },
)
BY_DAMAGE: Mapping[DamageType, DeathCause] = {spec.damage: cause for cause, spec in DEATH_CAUSES.items() if spec.damage is not None}


def death_cause_of(harm: HarmCause | None, damage: DamageType | None = None, default: DeathCause = DeathCause.UNKNOWN) -> DeathCause:
    if damage is not None and damage in BY_DAMAGE:
        return BY_DAMAGE[damage]
    return HARM_DEATHS.get(harm, default) if harm is not None else default


LOOSE_CAUSES = frozenset(cause for cause, spec in DEATH_CAUSES.items() if spec.loose)
