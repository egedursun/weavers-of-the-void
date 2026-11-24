from aerona.domain.enums.body import DamageType, HarmCause
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.discovery import AgeKind, AnomalyKind, EraDeed, GreatField, ResearchIncident
from aerona.domain.enums.media import RecordForm
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.records import WitnessMode
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.tongues import LanguageModality
from aerona.domain.enums.war import WarEnding

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


RANK = {WitnessMode.WAS_TOLD: 0, WitnessMode.HEARD: 1, WitnessMode.SENSED: 2, WitnessMode.SAW: 2, WitnessMode.TOOK_PART: 3}

TRANSLATE_SKILL_KINDS = (SkillKind.LANGUAGES, SkillKind.WRITING)
STRIKE_RESEARCH_INCIDENTS = frozenset({ResearchIncident.FIRE, ResearchIncident.EXPLOSION})
STRIKE_RESEARCH_INCIDENTS_2 = frozenset({ResearchIncident.EXPLOSION, ResearchIncident.POISONING, ResearchIncident.SUMMONING_GONE_WRONG, ResearchIncident.FIRE})
STRIKE_RESEARCH_INCIDENTS_3 = frozenset({ResearchIncident.RELEASED_BEAST, ResearchIncident.SUMMONING_GONE_WRONG})
ACCIDENTS_RESEARCH_INCIDENTS = (ResearchIncident.POISONING, ResearchIncident.EXPLOSION)
SETTLE_AGES_AGE_KINDS = frozenset({AgeKind.GOLDEN, AgeKind.HEROIC})
MEET_ANOMALIES_ANOMALY_KINDS = (AnomalyKind.CONTRARY_CURE,)

COMMON_ANOMALIES = (AnomalyKind.FAILED_PREDICTION, AnomalyKind.OBSERVATION)

PEACEFUL_ENDINGS = frozenset({WarEnding.PEACE, WarEnding.WHITE_PEACE})
RECOVERING_DEEDS = frozenset({EraDeed.FIRST_TECHNIQUE, EraDeed.GREAT_PERSON, EraDeed.FIRST_INSTITUTION})
LINGERING_AGES = frozenset({AgeKind.HEROIC, AgeKind.REBORN, AgeKind.WANDERING})
HEALING_BRANCHES = frozenset({KnowledgeBranch.MEDICINE, KnowledgeBranch.NATURAL_HISTORY})
TEACHING_BRANCHES = frozenset({KnowledgeBranch.WRITING, KnowledgeBranch.LANGUAGE_LORE, KnowledgeBranch.MATHEMATICS})
CODES = (Technique.WRITTEN_LAW, Technique.CODIFIED_LAW)
RETITLED = ((GreatField.HEALER, (SkillKind.MEDICINE, SkillKind.SURGERY)), (GreatField.LAWGIVER, (SkillKind.LAW,)))
TAKEN_SKILLS = frozenset(skill for _, kinds in RETITLED for skill in kinds)
MODALITY_RECORDS = {
    LanguageModality.SCENT: RecordForm.SCENT,
    LanguageModality.CHEMICAL: RecordForm.SCENT,
    LanguageModality.TACTILE: RecordForm.TACTILE,
    LanguageModality.VIBRATION: RecordForm.TACTILE,
}
