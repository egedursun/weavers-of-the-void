from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.culture import ArtMedium
from aerona.domain.enums.discovery import AnomalyKind, ArtDiscipline, TheoryDomain
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
        D.COSMOLOGY: DomainSpec("Cosmology", "the shape and workings of the heavens", (B.ASTRONOMY, B.SEAFARING, B.SKY_NAVIGATION)),
        D.MATTER: DomainSpec("Matter", "what things are made of", (B.METALLURGY, B.ARCHITECTURE)),
        D.LIFE: DomainSpec("Life", "how living things grow and change", (B.AGRICULTURE, B.BIOMANCY)),
        D.MIND: DomainSpec("Mind", "how minds think and feel", (B.WRITING,)),
        D.MAGIC: DomainSpec("Magic", "how workings take hold of the world", (B.MAGIC, B.FORBIDDEN)),
        D.HISTORY: DomainSpec("History", "what happened before", (B.WRITING,)),
        D.SOCIETY: DomainSpec("Society", "how peoples order themselves", (B.CIVICS, B.TRADE)),
    },
)

ANOMALIES: MappingProxyType[AnomalyKind, str] = total(
    AnomalyKind,
    {
        AnomalyKind.FAILED_PREDICTION: "A prediction failed",
        AnomalyKind.CONTRARY_CURE: "A cure worked against its teaching",
        AnomalyKind.OBSERVATION: "An observation it cannot explain",
        AnomalyKind.DIVINE_SIGN: "A god showed otherwise",
    },
)


@dataclass(frozen=True)
class DisciplineSpec:
    label: str
    structure: tuple[str, ...]
    media: tuple[ArtMedium, ...]
    skills: tuple[SkillKind, ...]
    verbal: bool = False


DISCIPLINES: MappingProxyType[ArtDiscipline, DisciplineSpec] = total(
    ArtDiscipline,
    {
        ArtDiscipline.MUSIC: DisciplineSpec("Music", ("scale", "rhythm", "voices", "instruments"), (ArtMedium.MUSIC, ArtMedium.SONG), (SkillKind.ORATORY,)),
        ArtDiscipline.POETRY: DisciplineSpec(
            "Poetry",
            ("metre", "rhyme", "stanza", "line_length", "subjects"),
            (ArtMedium.EPIC_POEM, ArtMedium.SONG),
            (SkillKind.WRITING, SkillKind.ORATORY),
            True,
        ),
        ArtDiscipline.DANCE: DisciplineSpec("Dance", ("tempo", "group_size", "movement"), (ArtMedium.DANCE,), (SkillKind.ORATORY,)),
        ArtDiscipline.THEATRE: DisciplineSpec("Theatre", ("form", "cast", "subjects"), (ArtMedium.PLAY,), (SkillKind.ORATORY, SkillKind.WRITING), True),
        ArtDiscipline.PAINTING: DisciplineSpec("Painting", ("palette", "motifs", "materials"), (ArtMedium.FRESCO, ArtMedium.MOSAIC), (SkillKind.POTTERY,)),
        ArtDiscipline.SCULPTURE: DisciplineSpec(
            "Sculpture", ("motifs", "materials", "scale"), (ArtMedium.STATUE, ArtMedium.CARVING), (SkillKind.MASONRY, SkillKind.CARPENTRY)
        ),
        ArtDiscipline.ARCHITECTURE_STYLE: DisciplineSpec(
            "Style of building", ("motifs", "materials", "proportions"), (ArtMedium.ARCHITECTURE_ORNAMENT,), (SkillKind.MASONRY, SkillKind.ENGINEERING)
        ),
        ArtDiscipline.TEXTILE: DisciplineSpec("Textile", ("palette", "motifs", "pattern"), (ArtMedium.TAPESTRY,), (SkillKind.WEAVING,)),
        ArtDiscipline.CALLIGRAPHY: DisciplineSpec("Calligraphy", ("script", "hand", "ornament"), (ArtMedium.BOOK,), (SkillKind.WRITING,), True),
    },
)

FORM_OF_MEDIUM: MappingProxyType[ArtMedium, ArtDiscipline] = MappingProxyType(
    {medium: discipline for discipline, spec in reversed(list(DISCIPLINES.items())) for medium in spec.media}
)
