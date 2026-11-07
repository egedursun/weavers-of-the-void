from dataclasses import dataclass, field
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.culture import BoostTrigger, Capability, IdeologyTenet, Technique
from aerona.domain.enums.faction import EstatePrivilege
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.polity import GovernmentKind, LawKind, OfficeKind
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.domain.enums.statecraft import TaxKind

T = Technique
B = KnowledgeBranch


@dataclass(frozen=True)
class TriggerSpec:
    label: str
    techniques: tuple[Technique, ...]


TRIGGERS: MappingProxyType[BoostTrigger, TriggerSpec] = total(
    BoostTrigger,
    {
        BoostTrigger.COASTAL_FISHING: TriggerSpec("Coastal fishing at scale", (T.SAILING, T.CARTOGRAPHY)),
        BoostTrigger.SURVIVED_SIEGE: TriggerSpec("Survived a siege", (T.FORTIFICATION, T.FORTRESS)),
        BoostTrigger.SURVIVED_EPIDEMIC: TriggerSpec("Survived an epidemic", (T.QUARANTINE, T.HERBALISM, T.HOSPITALS)),
        BoostTrigger.ECLIPSE_OBSERVED: TriggerSpec("An eclipse seen from an observatory", (T.ECLIPSE_PREDICTION, T.CALENDAR)),
        BoostTrigger.GREAT_TRIAL: TriggerSpec("A great trial", (T.WRITTEN_LAW, T.CODIFIED_LAW)),
        BoostTrigger.GREAT_DEBT: TriggerSpec("A great debt", (T.BANKING, T.DOUBLE_ENTRY)),
        BoostTrigger.STEPPE_HORSES_AT_WAR: TriggerSpec("Riders of the open plains at war", (T.HORSE_ARCHERY,)),
    },
)


@dataclass(frozen=True)
class SocialShift:
    values: dict[ValueAxis, int] = field(default_factory=dict)
    classes: dict[SocialClass, float] = field(default_factory=dict)


SOCIAL_CHANGE: MappingProxyType[Technique, SocialShift] = MappingProxyType(
    {
        T.PRINTING: SocialShift({ValueAxis.KNOWLEDGE: 8}, {SocialClass.SCRIBE: 1.0}),
        T.PRINTING_PRESS: SocialShift({ValueAxis.KNOWLEDGE: 10, ValueAxis.TRADITION: -4}, {SocialClass.SCRIBE: 1.0}),
        T.BANKING: SocialShift({ValueAxis.WEALTH: 8}, {SocialClass.MERCHANT: 1.0}),
        T.JOINT_STOCK: SocialShift({ValueAxis.WEALTH: 6}, {SocialClass.MERCHANT: 1.5}),
        T.BUREAUCRACY: SocialShift({ValueAxis.LAW: 6, ValueAxis.HIERARCHY: 4}, {SocialClass.SCRIBE: 2.0}),
        T.CODIFIED_LAW: SocialShift({ValueAxis.LAW: 8}, {}),
        T.NECROMANCY: SocialShift({ValueAxis.HONOUR: -6, ValueAxis.DEATH: 6}, {}),
        T.STEEL: SocialShift({ValueAxis.MARTIAL: 4}, {SocialClass.WARRIOR: 1.0}),
        T.HUMANIST_IDEALS: SocialShift({ValueAxis.HIERARCHY: -6, ValueAxis.KNOWLEDGE: 6}, {}),
        T.MONASTICISM: SocialShift({ValueAxis.PIETY: 6}, {SocialClass.MONASTIC: 1.0}),
        T.ORGANISED_CLERGY: SocialShift({ValueAxis.PIETY: 4, ValueAxis.HIERARCHY: 2}, {SocialClass.PRIEST: 1.0}),
        T.EMPIRICISM: SocialShift({ValueAxis.TRUTH: 6, ValueAxis.SUPERSTITION: -6}, {}),
        T.GUILDS: SocialShift({ValueAxis.CRAFTSMANSHIP: 6}, {SocialClass.ARTISAN: 1.0}),
        T.PLOUGH: SocialShift({}, {SocialClass.FARMER: -1.0, SocialClass.ARTISAN: 0.5}),
        T.UNIVERSITIES: SocialShift({ValueAxis.KNOWLEDGE: 6}, {SocialClass.SCRIBE: 1.0}),
    }
)

GOVERNMENT_GATES: MappingProxyType[GovernmentKind, Technique] = MappingProxyType(
    {
        GovernmentKind.REPUBLIC: T.WRITTEN_LAW,
        GovernmentKind.OLIGARCHY: T.WRITTEN_LAW,
        GovernmentKind.EMPIRE: T.BUREAUCRACY,
        GovernmentKind.THEOCRACY: T.ORGANISED_CLERGY,
    }
)
OFFICE_GATES: MappingProxyType[OfficeKind, Technique] = MappingProxyType(
    {
        OfficeKind.AMBASSADOR: T.DIPLOMATIC_CORPS,
        OfficeKind.GOVERNOR: T.WRITTEN_LAW,
        OfficeKind.COURT_SCHOLAR: T.LOGIC,
    }
)
LAW_GATES: MappingProxyType[LawKind, Technique] = MappingProxyType(
    {
        LawKind.PENAL_CODE: T.WRITTEN_LAW,
        LawKind.CONSTITUTION: T.CODIFIED_LAW,
        LawKind.GUILD_CHARTER: T.GUILDS,
        LawKind.STANDING_ARMY: T.STANDING_ARMY_ADMIN,
        LawKind.FRANCHISE: T.HUMANIST_IDEALS,
        LawKind.CENSORSHIP: T.WRITTEN_LAW,
        LawKind.DEBT_LAW: T.BANKING,
    }
)
TAX_GATES: MappingProxyType[TaxKind, Technique] = MappingProxyType(
    {
        TaxKind.POLL: T.CENSUS,
        TaxKind.TRADE: T.COINAGE,
        TaxKind.CONSUMPTION: T.DOUBLE_ENTRY,
        TaxKind.TITHE: T.ORGANISED_CLERGY,
    }
)
PRIVILEGE_GATES: MappingProxyType[EstatePrivilege, Technique] = MappingProxyType(
    {
        EstatePrivilege.MONOPOLY: T.GUILDS,
        EstatePrivilege.JUDICIAL_IMMUNITY: T.CODIFIED_LAW,
    }
)
TENET_GATES: MappingProxyType[IdeologyTenet, Technique] = MappingProxyType(
    {
        IdeologyTenet.RATIONALISM: T.LOGIC,
        IdeologyTenet.LEGALISM: T.WRITTEN_LAW,
        IdeologyTenet.EGALITARIANISM: T.HUMANIST_IDEALS,
        IdeologyTenet.MERCANTILISM: T.DOUBLE_ENTRY,
    }
)


@dataclass(frozen=True)
class CapabilitySpec:
    label: str
    branches: tuple[tuple[KnowledgeBranch, int], ...]
    all_of: tuple[Technique, ...] = ()
    any_of: tuple[Technique, ...] = ()
    effect: str = ""


CAPABILITIES: MappingProxyType[Capability, CapabilitySpec] = total(
    Capability,
    {
        Capability.BLUE_WATER_NAVIGATION: CapabilitySpec(
            "Blue-water navigation",
            ((B.ASTRONOMY, 2), (B.SHIPBUILDING, 1)),
            (T.CARTOGRAPHY,),
            (),
            "ships cross open seas and their voyages reach farther",
        ),
        Capability.UNIVERSITY: CapabilitySpec(
            "Universities can rise",
            ((B.WRITING, 2),),
            (T.LOGIC,),
            (T.ORGANISED_CLERGY, T.BANKING),
            "a university may be founded where scholars and wealth gather",
        ),
    },
)
CAPABILITY_INSTITUTIONS: MappingProxyType[Technique, Capability] = MappingProxyType({T.UNIVERSITIES: Capability.UNIVERSITY})
