from dataclasses import dataclass
from types import MappingProxyType

from aerona.catalog.art_modes import ART_MODES
from aerona.core.total import total
from aerona.domain.enums.culture import ArtMode
from aerona.domain.enums.discovery import AnomalyKind, TheoryDomain
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.society import KnowledgeBranch

D = TheoryDomain
B = KnowledgeBranch


@dataclass(frozen=True)
class DomainSpec:
    label: str
    subject: str
    branches: tuple[KnowledgeBranch, ...]


DOMAINS: MappingProxyType[TheoryDomain, DomainSpec] = total(
    TheoryDomain,
    {
        D.MEDICINE: DomainSpec("Medicine", "how sickness comes and goes", (B.MEDICINE,)),
        D.COSMOLOGY: DomainSpec("Cosmology", "the shape and workings of the heavens", (B.ASTRONOMY, B.SEAFARING, B.SKY_NAVIGATION, B.MATHEMATICS)),
        D.MATTER: DomainSpec("Matter", "what things are made of", (B.METALLURGY, B.ARCHITECTURE)),
        D.LIFE: DomainSpec("Life", "how living things grow and change", (B.AGRICULTURE, B.BIOMANCY, B.NATURAL_HISTORY)),
        D.MIND: DomainSpec("Mind", "how minds think and feel", (B.WRITING,)),
        D.MAGIC: DomainSpec("Magic", "how workings take hold of the world", (B.MAGIC, B.FORBIDDEN)),
        D.HISTORY: DomainSpec("History", "what happened before", (B.WRITING,)),
        D.SOCIETY: DomainSpec("Society", "how peoples order themselves", (B.CIVICS, B.TRADE)),
        D.LANGUAGE: DomainSpec("Language", "how tongues arise, change and part", (B.LANGUAGE_LORE, B.WRITING)),
        D.LAW: DomainSpec("Law", "what makes a rule binding and a judgement just", (B.LAW, B.CIVICS)),
    },
)

ANOMALIES: MappingProxyType[AnomalyKind, str] = total(
    AnomalyKind,
    {
        AnomalyKind.FAILED_PREDICTION: "A prediction failed",
        AnomalyKind.CONTRARY_CURE: "A cure worked against its teaching",
        AnomalyKind.OBSERVATION: "An observation it cannot explain",
        AnomalyKind.DIVINE_SIGN: "A god showed otherwise",
        AnomalyKind.CONTRARY_RECORD: "Old records disagree with it",
        AnomalyKind.OUT_OF_PLACE_FIND: "A find that does not fit the held account",
    },
)
ANOMALY_DOMAINS: MappingProxyType[AnomalyKind, tuple[TheoryDomain, ...]] = total(
    AnomalyKind,
    {
        AnomalyKind.FAILED_PREDICTION: (D.COSMOLOGY, D.MEDICINE, D.MATTER),
        AnomalyKind.CONTRARY_CURE: (D.MEDICINE,),
        AnomalyKind.OBSERVATION: (D.COSMOLOGY, D.MATTER, D.LIFE),
        AnomalyKind.DIVINE_SIGN: (D.MAGIC,),
        AnomalyKind.CONTRARY_RECORD: (D.HISTORY, D.LANGUAGE, D.LAW, D.SOCIETY),
        AnomalyKind.OUT_OF_PLACE_FIND: (D.HISTORY, D.LIFE, D.COSMOLOGY),
    },
)
RECORDED_ANOMALIES = (AnomalyKind.CONTRARY_RECORD, AnomalyKind.OUT_OF_PLACE_FIND)


@dataclass(frozen=True)
class DisciplineSpec:
    label: str
    structure: tuple[str, ...]
    media: tuple[ArtMode, ...]
    skills: tuple[SkillKind, ...]
    verbal: bool = False


DISCIPLINES: MappingProxyType[ArtMode, DisciplineSpec] = MappingProxyType(
    {mode: DisciplineSpec(spec.label, spec.structure, (mode,), spec.skills, spec.verbal) for mode, spec in ART_MODES.items()}
)

FORM_OF_MEDIUM: MappingProxyType[ArtMode, ArtMode] = MappingProxyType({mode: mode for mode in ArtMode})
