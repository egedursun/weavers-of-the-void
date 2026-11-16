from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.culture import ItemClass, Technique
from aerona.domain.enums.discovery import AgeKind, BlueprintKind, BlueprintSource, EraDeed, GreatField, ResearchIncident
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import ActKind, SkillKind
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.domain.enums.structure import StructureKind

T = Technique
B = KnowledgeBranch
K = SkillKind
R = ResearchIncident
S = StructureKind


@dataclass(frozen=True)
class FieldSpec:
    label: str
    skills: tuple[SkillKind, ...]
    social_class: SocialClass
    structures: tuple[StructureKind, ...]
    deed: str


FIELDS: MappingProxyType[GreatField, FieldSpec] = total(
    GreatField,
    {
        GreatField.SCHOLAR: FieldSpec(
            "Great scholar",
            (K.LORE, K.WRITING, K.ASTRONOMY, K.MEDICINE, K.LAW, K.ALCHEMY),
            SocialClass.SCRIBE,
            (S.LIBRARY, S.SCHOOL, S.ACADEMY, S.OBSERVATORY),
            "a breakthrough completes the technique their scholars pursue",
        ),
        GreatField.ARTIST: FieldSpec(
            "Great artist",
            (K.ORATORY, K.WRITING, K.JEWELLING, K.WEAVING, K.POTTERY, K.CARPENTRY),
            SocialClass.ARTISAN,
            (S.THEATRE, S.MONUMENT, S.ARENA),
            "a great work raises the prestige of their tongue",
        ),
        GreatField.GENERAL: FieldSpec(
            "Great general",
            (K.TACTICS, K.STRATEGY, K.LEADERSHIP, K.LOGISTICS),
            SocialClass.WARRIOR,
            (S.FORT, S.CITADEL, S.TOWER),
            "a campaign raises the morale of the realm's armies",
        ),
        GreatField.PROPHET: FieldSpec(
            "Great prophet",
            (K.THEOLOGY, K.PROPHECY, K.RITUAL, K.ORATORY),
            SocialClass.PRIEST,
            (S.TEMPLE, S.SHRINE, S.MONASTERY),
            "a doctrine raises the zeal of their faith",
        ),
        GreatField.ENGINEER: FieldSpec(
            "Great engineer",
            (K.ENGINEERING, K.MASONRY, K.CARPENTRY, K.SMITHING),
            SocialClass.ARTISAN,
            (S.WORKSHOP, S.FORGE, S.MILL, S.AQUEDUCT),
            "a building rush hastens every work under construction",
        ),
        GreatField.MERCHANT: FieldSpec(
            "Great merchant",
            (K.NEGOTIATION, K.ACCOUNTING, K.ETIQUETTE),
            SocialClass.MERCHANT,
            (S.MARKET, S.BANK, S.WAREHOUSE, S.CARAVANSERAI),
            "a trade monopoly fills the treasury",
        ),
        GreatField.EXPLORER: FieldSpec(
            "Great explorer",
            (K.NAVIGATION, K.SAILING, K.TRACKING, K.MOUNTAINEERING),
            SocialClass.WARRIOR,
            (S.HARBOUR, S.WATCHTOWER),
            "a discovery charts the lands around their realm",
        ),
    },
)

AGES: MappingProxyType[AgeKind, str] = total(
    AgeKind,
    {
        AgeKind.NORMAL: "An ordinary age",
        AgeKind.GOLDEN: "A golden age",
        AgeKind.DARK: "A dark age",
        AgeKind.HEROIC: "A heroic age",
        AgeKind.RISING: "A rising age",
        AgeKind.DECLINING: "A declining age",
        AgeKind.TRANSFORMING: "An age of change",
        AgeKind.STAGNANT: "A still age",
    },
)

DEEDS: MappingProxyType[EraDeed, str] = total(
    EraDeed,
    {
        EraDeed.FIRST_TECHNIQUE: "First in the world to know a technique",
        EraDeed.FIRST_INSTITUTION: "Birthplace of an institution",
        EraDeed.GREAT_VICTORY: "Won a war",
        EraDeed.WONDER: "Raised a wonder",
        EraDeed.GREAT_PERSON: "A great person rose",
        EraDeed.DEFEAT: "Lost a war",
        EraDeed.FAMINE: "Famine in its lands",
        EraDeed.FIRST_NETWORK: "First to join its lands by a network",
        EraDeed.FIRST_MADE_MIND: "First to make a mind",
        EraDeed.FIRST_LINE: "First to shape a living line",
        EraDeed.REVELATION: "A hidden truth came to light",
        EraDeed.COLLAPSE: "Its order collapsed",
    },
)

INCIDENTS: MappingProxyType[ResearchIncident, str] = total(
    ResearchIncident,
    {
        R.LEAK: "The secret leaked",
        R.RELEASED_BEAST: "A beast got loose",
        R.PLAGUE: "A sickness got loose",
        R.BACKLASH: "A working turned back on its makers",
        R.FIRE: "A fire in the workshop",
        R.EXPLOSION: "An explosion",
        R.POISONING: "A poisoning",
        R.SUMMONING_GONE_WRONG: "A summoning gone wrong",
    },
)


@dataclass(frozen=True)
class DangerSpec:
    act: ActKind
    incidents: tuple[ResearchIncident, ...]


DANGEROUS_TECHNIQUES: MappingProxyType[Technique, DangerSpec] = MappingProxyType(
    {
        T.NECROMANCY: DangerSpec(ActKind.NECROMANCY, (R.PLAGUE, R.LEAK, R.BACKLASH)),
        T.SUMMONING: DangerSpec(ActKind.MAGIC_USE, (R.SUMMONING_GONE_WRONG, R.RELEASED_BEAST)),
        T.SKYSTEEL: DangerSpec(ActKind.MAGIC_USE, (R.EXPLOSION, R.BACKLASH)),
    }
)


@dataclass(frozen=True)
class BranchDanger:
    level: int
    act: ActKind
    incidents: tuple[ResearchIncident, ...]


DANGEROUS_BRANCHES: MappingProxyType[KnowledgeBranch, BranchDanger] = MappingProxyType(
    {
        B.FORBIDDEN: BranchDanger(1, ActKind.BLOOD_MAGIC, (R.BACKLASH, R.LEAK, R.PLAGUE)),
        B.VOID_LIVING: BranchDanger(3, ActKind.VOID_MAGIC, (R.BACKLASH, R.EXPLOSION)),
        B.BIOMANCY: BranchDanger(3, ActKind.MAGIC_USE, (R.PLAGUE, R.RELEASED_BEAST)),
        B.IMMORTALITY: BranchDanger(3, ActKind.NECROMANCY, (R.BACKLASH, R.POISONING)),
    }
)

ACCIDENT_BRANCHES: MappingProxyType[KnowledgeBranch, tuple[ResearchIncident, ...]] = MappingProxyType(
    {
        B.MAGIC: (R.SUMMONING_GONE_WRONG, R.FIRE, R.POISONING),
        B.METALLURGY: (R.FIRE, R.EXPLOSION),
        B.ARCHITECTURE: (R.EXPLOSION, R.FIRE),
        B.MEDICINE: (R.POISONING,),
    }
)

ITEM_MATERIALS: MappingProxyType[MaterialKind, Technique] = MappingProxyType(
    {
        MaterialKind.BRONZE: T.BRONZE,
        MaterialKind.IRON: T.IRON,
        MaterialKind.STEEL: T.STEEL,
        MaterialKind.SKYSTEEL: T.SKYSTEEL,
        MaterialKind.STAR_METAL: T.SKYSTEEL,
    }
)
ITEM_CLASSES: MappingProxyType[ItemClass, Technique] = MappingProxyType(
    {
        ItemClass.MAP: T.CARTOGRAPHY,
        ItemClass.ASTROLABE: T.ASTRONOMY_INSTRUMENTS,
        ItemClass.CROSSBOW: T.IRON,
        ItemClass.PROSTHESIS: T.PROSTHETICS,
        ItemClass.CURRENCY: T.COINAGE,
        ItemClass.BOOK: T.PAPER,
        ItemClass.FIREARM: T.STEEL,
        ItemClass.IMPLANT: T.PROSTHETICS,
        ItemClass.DRUG: T.ALCHEMY,
    }
)

STRUCTURE_SUPERSEDED: MappingProxyType[Technique, tuple[StructureKind, ...]] = MappingProxyType(
    {
        T.FORTIFICATION: (S.WALL, S.WATCHTOWER, S.GATE),
        T.FORTRESS: (S.FORT, S.TOWER, S.CITADEL),
        T.AQUEDUCT: (S.IRRIGATION,),
        T.ASTRONOMY_INSTRUMENTS: (S.OBSERVATORY,),
        T.UNIVERSITIES: (S.SCHOOL, S.ACADEMY),
        T.HOSPITALS: (S.HOSPITAL,),
        T.BANKING: (S.BANK,),
    }
)

BLUEPRINT_KINDS: MappingProxyType[BlueprintKind, str] = total(
    BlueprintKind,
    {
        BlueprintKind.VESSEL: "Ship design",
        BlueprintKind.SIEGE_ENGINE: "Siege engine design",
        BlueprintKind.STRUCTURE: "Building plan",
        BlueprintKind.ARTIFACT_PATTERN: "Pattern of a crafted thing",
        BlueprintKind.MADE_BODY: "Design of a made body",
        BlueprintKind.AUGMENT: "Design of an augment",
        BlueprintKind.LINE: "Pattern of a living line",
        BlueprintKind.NETWORK: "Plan of a network",
        BlueprintKind.RITE_PATTERN: "Pattern of a rite",
    },
)
BLUEPRINT_SOURCES: MappingProxyType[BlueprintSource, str] = total(
    BlueprintSource,
    {
        BlueprintSource.DRAWN: "Drawn by its own makers",
        BlueprintSource.STOLEN: "Stolen",
        BlueprintSource.TRADED: "Bought in trade",
        BlueprintSource.LICENSED: "Used under licence",
        BlueprintSource.GRANTED: "Granted by a god",
    },
)

ERA_NAMES = ("First era", "Second era", "Third era", "Fourth era", "Fifth era", "Sixth era")


def era_name(era: int) -> str:
    return ERA_NAMES[era - 1] if 0 < era <= len(ERA_NAMES) else f"Era {era}"
