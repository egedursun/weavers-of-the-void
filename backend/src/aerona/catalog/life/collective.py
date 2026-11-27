from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from aerona.catalog.collective import ACTS
from aerona.core.total import total
from aerona.domain.enums.collective import AccountKind, AccountMedium, AccountStance, CollectiveActKind, CrowdFeeling, RoleKind
from aerona.domain.enums.mind import Facet, ValueAxis
from aerona.domain.enums.mortal import CareerPath
from aerona.domain.enums.relations import InteractionKind
from aerona.domain.enums.vehicles import VehicleSection

MEDIUM_FADE: Mapping[AccountMedium, int] = total(
    AccountMedium,
    {
        AccountMedium.ORAL: 100,
        AccountMedium.BOOK: 0,
        AccountMedium.INSCRIPTION: 0,
        AccountMedium.ARTWORK: 0,
        AccountMedium.RECORD: 0,
        AccountMedium.PERFORMANCE: 50,
        AccountMedium.MIND_STATE: 10,
        AccountMedium.MARKS: 20,
    },
)

MEDIUM_PHRASES: Mapping[AccountMedium, str] = total(
    AccountMedium,
    {
        AccountMedium.ORAL: "word of mouth",
        AccountMedium.BOOK: "writing in books",
        AccountMedium.INSCRIPTION: "inscription",
        AccountMedium.ARTWORK: "works of art",
        AccountMedium.RECORD: "written records",
        AccountMedium.PERFORMANCE: "performance",
        AccountMedium.MIND_STATE: "held states of mind",
        AccountMedium.MARKS: "marks",
    },
)


CONFORMING = (Facet.COOPERATION, Facet.POLITENESS, Facet.SENSE_OF_DUTY)


TRIGGER_MOOD: Mapping[CollectiveActKind, CrowdFeeling] = MappingProxyType({act: spec.feeling for act, spec in ACTS.items()})


MOUNT_FALLBACKS = (
    VehicleSection.DECK,
    VehicleSection.PLATFORM,
    VehicleSection.TURRET,
    VehicleSection.HULL,
    VehicleSection.CHASSIS,
    VehicleSection.FRAME,
    VehicleSection.GONDOLA,
    VehicleSection.MOUNT_BODY,
    VehicleSection.CORE,
)


FEARFUL = (ValueAxis.SUPERSTITION, ValueAxis.DEATH, ValueAxis.PIETY)


CAREER_ROLES: MappingProxyType[CareerPath, RoleKind] = MappingProxyType(
    {
        CareerPath.ARMY: RoleKind.COMBAT,
        CareerPath.OFFICE: RoleKind.OFFICE,
        CareerPath.APPRENTICE: RoleKind.PROFESSION,
        CareerPath.TRADE: RoleKind.PROFESSION,
        CareerPath.VOWS: RoleKind.PRIESTHOOD,
        CareerPath.STUDY: RoleKind.PROFESSION,
    }
)

DEEPER_BEHAVIOUR_INTERACTION_KINDS = (InteractionKind.TEACH, InteractionKind.GOSSIP)


@dataclass(frozen=True)
class AccountKindSpec:
    label: str
    decay: int
    remembers: bool
    backs_claims: bool = False
    sung: bool = False


K = AccountKind
ACCOUNT_KINDS = total(
    AccountKind,
    {
        K.OFFICIAL_CHRONICLE: AccountKindSpec("Official chronicle", 100, False),
        K.FOLK_MEMORY: AccountKindSpec("Folk memory", 120, True),
        K.FOREIGN_ACCOUNT: AccountKindSpec("Foreign account", 100, True),
        K.GOSPEL: AccountKindSpec("Sacred account", 60, False),
        K.EPIC: AccountKindSpec("Epic", 80, True),
        K.INSCRIPTION: AccountKindSpec("Inscription", 30, False),
        K.FOUNDING_MYTH: AccountKindSpec("Founding myth", 50, False),
        K.ELDER_MEMORY: AccountKindSpec("Elder memory", 140, False),
        K.RECORD: AccountKindSpec("Record", 20, False),
        K.TESTIMONY: AccountKindSpec("Testimony", 110, False),
        K.GENEALOGY: AccountKindSpec("Genealogy", 40, False, backs_claims=True),
        K.SONG: AccountKindSpec("Song", 30, True, sung=True),
        K.TRAVEL_ACCOUNT: AccountKindSpec("Travel account", 90, True),
        K.LAW_RECORD: AccountKindSpec("Law record", 20, False, backs_claims=True),
    },
)


@dataclass(frozen=True)
class AccountStanceSpec:
    label: str
    slant: int
    standing_rule: str
    praises: bool = False
    hides: bool = False
    grieves: bool = False


S_ = AccountStance
ACCOUNT_STANCES = total(
    AccountStance,
    {
        S_.GLORIFY: AccountStanceSpec("Glorifies", 8, "glorify_standing_effect", praises=True),
        S_.VILIFY: AccountStanceSpec("Vilifies", 8, "vilify_standing_effect"),
        S_.OMIT: AccountStanceSpec("Leaves out", 15, "omit_standing_effect", hides=True),
        S_.NEUTRAL: AccountStanceSpec("Tells plainly", 0, "neutral_standing_effect"),
        S_.JUSTIFY: AccountStanceSpec("Admits and justifies", 5, "justify_standing_effect"),
        S_.LAMENT: AccountStanceSpec("Laments", 4, "lament_standing_effect", grieves=True),
        S_.MOCK: AccountStanceSpec("Mocks", 10, "mock_standing_effect"),
        S_.WARN: AccountStanceSpec("Warns", 6, "warn_standing_effect"),
    },
)
REMEMBERING_KINDS = tuple(kind for kind, spec in ACCOUNT_KINDS.items() if spec.remembers)
