from aerona.catalog.careers import CAREERS, OPEN_PATHS
from aerona.core.total import partial
from aerona.domain.enums.body import InjuryKind
from aerona.domain.enums.mind import MemoryKind, NeedKind, TraitKind, ValueAxis
from aerona.domain.enums.mortal import CareerPath, LifeStage, PunishmentKind, StressBreak

GRATEFUL = (MemoryKind.SAVED_ME, MemoryKind.GIFTED_ME, MemoryKind.TAUGHT_ME, MemoryKind.FREED_US)


BREAK_TRAITS: dict[StressBreak, frozenset[TraitKind]] = {
    StressBreak.RAGE: frozenset({TraitKind.WRATHFUL, TraitKind.CRUEL, TraitKind.RECKLESS, TraitKind.VENGEFUL}),
    StressBreak.FLIGHT: frozenset({TraitKind.CRAVEN, TraitKind.FICKLE, TraitKind.PARANOID}),
    StressBreak.DESPAIR: frozenset({TraitKind.MELANCHOLIC, TraitKind.RECLUSIVE}),
    StressBreak.ZEAL: frozenset({TraitKind.ZEALOUS, TraitKind.ASCETIC, TraitKind.IMPRESSIONABLE}),
    StressBreak.VICE: frozenset({TraitKind.GLUTTONOUS, TraitKind.LUSTFUL, TraitKind.GREEDY}),
    StressBreak.REVELATION: frozenset({TraitKind.CURIOUS, TraitKind.SCHOLARLY}),
    StressBreak.WITHDRAWAL: frozenset({TraitKind.RECLUSIVE, TraitKind.FRAGILE, TraitKind.DETACHED, TraitKind.ALOOF}),
}


CAREER_ROLES = partial(
    CareerPath,
    {path: spec.role for path, spec in CAREERS.items() if spec.role is not None},
    without={CareerPath.STAY},
)
CAREER_TRAITS: dict[CareerPath, frozenset[TraitKind]] = {path: spec.traits for path, spec in CAREERS.items() if spec.traits}
CAREER_VALUES: dict[CareerPath, ValueAxis] = {path: spec.value for path, spec in CAREERS.items() if spec.value is not None}
CAREER_NEEDS: dict[CareerPath, NeedKind] = {path: spec.need for path, spec in CAREERS.items() if spec.need is not None}


MUTILATION_KINDS: dict[PunishmentKind, InjuryKind] = {
    PunishmentKind.HAND: InjuryKind.SEVERED,
    PunishmentKind.TONGUE: InjuryKind.SEVERED,
    PunishmentKind.EYES: InjuryKind.GOUGED,
}

OPENINGS_CAREER_PATHS = OPEN_PATHS
OPENINGS_LIFE_STAGES_2 = (LifeStage.YOUTH, LifeStage.ADULT)
CHOOSE_PATH_LIFE_STAGES = (LifeStage.YOUTH, LifeStage.ADULT)
SEED_STANDING_MEMORY_KINDS = (MemoryKind.MAIMED_ME, MemoryKind.KILLED_KIN, MemoryKind.HARMED_ME)
LIVE_ONE_EPOCH_LIFE_STAGES = (LifeStage.ELDER, LifeStage.ANCIENT)
EDUCATE_LIFE_STAGES = (LifeStage.CHILD, LifeStage.YOUTH)
BETROTH_CHILDREN_LIFE_STAGES = (LifeStage.CHILD, LifeStage.YOUTH)
