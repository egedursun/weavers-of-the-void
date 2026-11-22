from aerona.core.total import partial
from aerona.domain.enums.body import InjuryKind
from aerona.domain.enums.entity import MortalRole
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
}


CAREER_ROLES = partial(
    CareerPath,
    {
        CareerPath.ARMY: MortalRole.WARRIOR,
        CareerPath.OFFICE: MortalRole.SCRIBE,
        CareerPath.APPRENTICE: MortalRole.APPRENTICE,
        CareerPath.VOWS: MortalRole.PRIEST,
        CareerPath.TRADE: MortalRole.MERCHANT,
        CareerPath.WANDER: MortalRole.EXPLORER,
        CareerPath.BANDIT: MortalRole.BANDIT,
        CareerPath.STUDY: MortalRole.SCIENTIST,
    },
    without={CareerPath.STAY},
)


CAREER_TRAITS: dict[CareerPath, frozenset[TraitKind]] = {
    CareerPath.ARMY: frozenset({TraitKind.BRAVE, TraitKind.WRATHFUL, TraitKind.RECKLESS, TraitKind.CUNNING_TACTICIAN}),
    CareerPath.OFFICE: frozenset({TraitKind.AMBITIOUS, TraitKind.JUST, TraitKind.PROUD}),
    CareerPath.APPRENTICE: frozenset({TraitKind.PATIENT, TraitKind.HUMBLE, TraitKind.CURIOUS}),
    CareerPath.VOWS: frozenset({TraitKind.ZEALOUS, TraitKind.ASCETIC, TraitKind.CHASTE}),
    CareerPath.TRADE: frozenset({TraitKind.GREEDY, TraitKind.GREGARIOUS, TraitKind.DECEITFUL}),
    CareerPath.WANDER: frozenset({TraitKind.CURIOUS, TraitKind.RECKLESS, TraitKind.FICKLE}),
    CareerPath.BANDIT: frozenset({TraitKind.CRUEL, TraitKind.GREEDY, TraitKind.DECEITFUL}),
    CareerPath.STUDY: frozenset({TraitKind.CURIOUS, TraitKind.SCHOLARLY, TraitKind.PATIENT}),
}


CAREER_VALUES: dict[CareerPath, ValueAxis] = {
    CareerPath.ARMY: ValueAxis.MARTIAL,
    CareerPath.OFFICE: ValueAxis.HIERARCHY,
    CareerPath.APPRENTICE: ValueAxis.TRADITION,
    CareerPath.VOWS: ValueAxis.PIETY,
    CareerPath.TRADE: ValueAxis.WEALTH,
    CareerPath.WANDER: ValueAxis.XENOPHILIA,
    CareerPath.STUDY: ValueAxis.KNOWLEDGE,
}


CAREER_NEEDS: dict[CareerPath, NeedKind] = {
    CareerPath.ARMY: NeedKind.STATUS,
    CareerPath.OFFICE: NeedKind.STATUS,
    CareerPath.APPRENTICE: NeedKind.PURPOSE,
    CareerPath.VOWS: NeedKind.FAITH,
    CareerPath.TRADE: NeedKind.SUSTENANCE,
    CareerPath.WANDER: NeedKind.PURPOSE,
    CareerPath.BANDIT: NeedKind.SUSTENANCE,
    CareerPath.STUDY: NeedKind.PURPOSE,
}


MUTILATION_KINDS: dict[PunishmentKind, InjuryKind] = {
    PunishmentKind.HAND: InjuryKind.SEVERED,
    PunishmentKind.TONGUE: InjuryKind.SEVERED,
    PunishmentKind.EYES: InjuryKind.GOUGED,
}

OPENINGS_CAREER_PATHS = frozenset({CareerPath.STAY, CareerPath.TRADE, CareerPath.WANDER, CareerPath.VOWS})
OPENINGS_LIFE_STAGES_2 = (LifeStage.YOUTH, LifeStage.ADULT)
CHOOSE_PATH_LIFE_STAGES = (LifeStage.YOUTH, LifeStage.ADULT)
SEED_STANDING_MEMORY_KINDS = (MemoryKind.MAIMED_ME, MemoryKind.KILLED_KIN, MemoryKind.HARMED_ME)
LIVE_ONE_EPOCH_LIFE_STAGES = (LifeStage.ELDER, LifeStage.ANCIENT)
EDUCATE_LIFE_STAGES = (LifeStage.CHILD, LifeStage.YOUTH)
BETROTH_CHILDREN_LIFE_STAGES = (LifeStage.CHILD, LifeStage.YOUTH)
