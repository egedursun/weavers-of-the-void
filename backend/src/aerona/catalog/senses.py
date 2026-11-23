from collections.abc import Mapping
from dataclasses import dataclass, field

from aerona.core.total import total
from aerona.domain.enums.demography import NaturalTrait
from aerona.domain.enums.nature import SenseCause, SenseKind

S = SenseKind
C = SenseCause
AGENTS = "agents"
NIGHT = "night"
AMBUSH = "ambush"
TRACKING = "tracking"
NAVIGATION = "navigation"
SPIRITS = "spirits"
SENSE_PURPOSES = (AGENTS, NIGHT, AMBUSH, TRACKING, NAVIGATION, SPIRITS)


@dataclass(frozen=True)
class SenseSpec:
    cause: SenseCause
    purposes: Mapping[str, float] = field(default_factory=dict)
    people_base: bool = False
    people_trait: NaturalTrait | None = None
    told: bool = False


SENSES: Mapping[SenseKind, SenseSpec] = total(
    SenseKind,
    {
        S.SIGHT: SenseSpec(C.BASE, {TRACKING: 0.2, NAVIGATION: 0.3}, people_base=True),
        S.NIGHT_VISION: SenseSpec(C.NOCTURNAL, {NIGHT: 0.6}, people_trait=NaturalTrait.DARK_SIGHT),
        S.SMELL: SenseSpec(C.FLESH_SEEKER, {AGENTS: 0.6, AMBUSH: 0.3, TRACKING: 0.5}, people_trait=NaturalTrait.KEEN_SENSES),
        S.HEARING: SenseSpec(C.PLANT_EATER, {AGENTS: 0.2, AMBUSH: 0.5}, people_base=True, people_trait=NaturalTrait.KEEN_SENSES),
        S.ECHOLOCATION: SenseSpec(C.ECHOLOCATION, {NIGHT: 0.2}),
        S.VIBRATION: SenseSpec(C.BURROWING, {AMBUSH: 0.2, TRACKING: 0.15}, people_trait=NaturalTrait.BURROWING),
        S.MAGNETIC: SenseSpec(C.MIGRATORY, {NAVIGATION: 0.7}),
        S.SPIRIT_SIGHT: SenseSpec(C.SPIRIT_SIGHT, {AGENTS: 0.2, SPIRITS: 1.0}),
        S.HEAT: SenseSpec(C.COLD_HUNTER, {NIGHT: 0.2, TRACKING: 0.15}),
        S.ELECTRIC: SenseSpec(C.WATER_HUNTER, {AGENTS: 0.3, AMBUSH: 0.4}, told=True),
        S.ULTRAVIOLET: SenseSpec(C.FLOWER_SEEKER, {TRACKING: 0.3, NAVIGATION: 0.1}, told=True),
    },
)

RAW_PURPOSES: Mapping[str, Mapping[SenseKind, float]] = {
    purpose: {sense: spec.purposes[purpose] for sense, spec in SENSES.items() if purpose in spec.purposes} for purpose in SENSE_PURPOSES
}
PURPOSES: Mapping[str, Mapping[SenseKind, float]] = {
    purpose: {sense: weight / sum(weights.values()) for sense, weight in weights.items()} for purpose, weights in RAW_PURPOSES.items()
}
