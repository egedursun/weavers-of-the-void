from aerona.domain.enums.body import DamageType, HarmCause
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.discovery import AgeKind, AnomalyKind, ResearchIncident
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.records import WitnessMode

PERFORMERS = (SkillKind.ORATORY, SkillKind.LORE)


HARMS = {
    ResearchIncident.FIRE: (HarmCause.EXPERIMENT, DamageType.FIRE),
    ResearchIncident.EXPLOSION: (HarmCause.EXPERIMENT, DamageType.EXPLOSIVE),
    ResearchIncident.POISONING: (HarmCause.POISON, DamageType.VENOM),
    ResearchIncident.SUMMONING_GONE_WRONG: (HarmCause.MAGIC_BACKLASH, DamageType.MAGIC),
}


BARD_SKILLS = (SkillKind.ORATORY, SkillKind.LORE)


PRINTED = (Technique.PRINTING, Technique.PRINTING_PRESS)


SCHOLARLY = (SkillKind.LORE, SkillKind.THEOLOGY, SkillKind.WRITING, SkillKind.ASTRONOMY, SkillKind.MEDICINE, SkillKind.LAW, SkillKind.ALCHEMY)


RANK = {WitnessMode.WAS_TOLD: 0, WitnessMode.HEARD: 1, WitnessMode.SAW: 2, WitnessMode.TOOK_PART: 3}

TRANSLATE_SKILL_KINDS = (SkillKind.LANGUAGES, SkillKind.WRITING)
STRIKE_RESEARCH_INCIDENTS = frozenset({ResearchIncident.FIRE, ResearchIncident.EXPLOSION})
STRIKE_RESEARCH_INCIDENTS_2 = frozenset({ResearchIncident.EXPLOSION, ResearchIncident.POISONING, ResearchIncident.SUMMONING_GONE_WRONG, ResearchIncident.FIRE})
STRIKE_RESEARCH_INCIDENTS_3 = frozenset({ResearchIncident.RELEASED_BEAST, ResearchIncident.SUMMONING_GONE_WRONG})
ACCIDENTS_RESEARCH_INCIDENTS = (ResearchIncident.POISONING, ResearchIncident.EXPLOSION)
SETTLE_AGES_AGE_KINDS = frozenset({AgeKind.GOLDEN, AgeKind.HEROIC})
MEET_ANOMALIES_ANOMALY_KINDS = (AnomalyKind.CONTRARY_CURE,)

COMMON_ANOMALIES = (AnomalyKind.FAILED_PREDICTION, AnomalyKind.OBSERVATION)
