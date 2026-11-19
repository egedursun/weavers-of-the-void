from dataclasses import dataclass
from types import MappingProxyType

from aerona.catalog.kinds.labels import spoken_labels
from aerona.core.total import partial, total
from aerona.db.kind_concepts.spec import ConceptSpec, KindProperty
from aerona.db.tables.society_kinds import OrganisationKindRow, ProfessionKindRow, RankKindRow
from aerona.domain.enums.demography import Job
from aerona.domain.enums.faction import FactionKind, FactionScale
from aerona.domain.enums.kinds import KindConcept
from aerona.domain.enums.mind import Profession
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_kinds import (
    OrganisationGovernance,
    OrganisationLegalForm,
    OrganisationMembership,
    OrganisationOwnership,
    OrganisationPurpose,
    ProfessionCategory,
)

PC = ProfessionCategory
OP = OrganisationPurpose
OW = OrganisationOwnership
OM = OrganisationMembership
OL = OrganisationLegalForm
OG = OrganisationGovernance
FS = FactionScale


@dataclass(frozen=True)
class BuiltInProfession:
    category: ProfessionCategory
    prestige: int
    income: int
    purity: int
    mishap_exposure: int
    skill_need: int


@dataclass(frozen=True)
class BuiltInRank:
    standing: int
    privilege: int
    duty: int
    mobility: int
    purity: int


@dataclass(frozen=True)
class BuiltInOrganisation:
    category: OrganisationPurpose
    ownership: OrganisationOwnership
    membership: OrganisationMembership
    scale: FactionScale
    legal_form: OrganisationLegalForm
    governance: OrganisationGovernance
    prestige: int
    cohesion: int
    secrecy: int
    foundable: bool = True


BUILT_IN_PROFESSIONS: MappingProxyType[Profession, BuiltInProfession] = total(
    Profession,
    {
        Profession.SOLDIER: BuiltInProfession(PC.WAR, 40, 30, 50, 60, 40),
        Profession.RIDER: BuiltInProfession(PC.TRANSPORT, 35, 30, 45, 40, 40),
        Profession.SMITH: BuiltInProfession(PC.CRAFTING, 40, 45, 40, 35, 55),
        Profession.BUILDER: BuiltInProfession(PC.BUILDING, 30, 35, 45, 40, 40),
        Profession.WEAVER: BuiltInProfession(PC.CRAFTING, 25, 30, 50, 10, 40),
        Profession.HEALER: BuiltInProfession(PC.HEALING, 55, 40, 40, 20, 60),
        Profession.SCHOLAR: BuiltInProfession(PC.LEARNING, 60, 35, 60, 5, 70),
        Profession.PRIEST: BuiltInProfession(PC.FAITH, 65, 30, 70, 5, 55),
        Profession.SORCERER: BuiltInProfession(PC.MAGIC, 50, 40, 40, 40, 75),
        Profession.MERCHANT: BuiltInProfession(PC.TRADE, 45, 65, 50, 15, 45),
        Profession.DIPLOMAT: BuiltInProfession(PC.RULE_AND_ADMINISTRATION, 60, 50, 60, 15, 60),
        Profession.HUNTER: BuiltInProfession(PC.FOOD_PRODUCTION, 30, 25, 35, 45, 35),
        Profession.SAILOR: BuiltInProfession(PC.TRANSPORT, 30, 30, 45, 50, 40),
        Profession.COMMANDER: BuiltInProfession(PC.WAR, 65, 50, 50, 50, 65),
        Profession.ENGINEER: BuiltInProfession(PC.SCIENCE_AND_ENGINEERING, 55, 60, 55, 20, 70),
        Profession.SCIENTIST: BuiltInProfession(PC.SCIENCE_AND_ENGINEERING, 60, 55, 60, 10, 75),
        Profession.PILOT: BuiltInProfession(PC.TRANSPORT, 50, 55, 55, 40, 60),
        Profession.TECHNICIAN: BuiltInProfession(PC.SCIENCE_AND_ENGINEERING, 40, 45, 50, 25, 55),
        Profession.PROGRAMMER: BuiltInProfession(PC.INFORMATION, 50, 60, 55, 5, 65),
        Profession.MECHANIC: BuiltInProfession(PC.CRAFTING, 35, 40, 45, 35, 50),
        Profession.MINER: BuiltInProfession(PC.EXTRACTION, 20, 30, 30, 60, 30),
        Profession.FARMER: BuiltInProfession(PC.FOOD_PRODUCTION, 25, 25, 50, 25, 25),
        Profession.ARTIST: BuiltInProfession(PC.ART_AND_ENTERTAINMENT, 45, 30, 55, 5, 55),
        Profession.ADMINISTRATOR: BuiltInProfession(PC.RULE_AND_ADMINISTRATION, 50, 50, 55, 5, 50),
        Profession.SPACER: BuiltInProfession(PC.EXPLORATION, 45, 50, 50, 55, 55),
        Profession.DEATH_WORKER: BuiltInProfession(PC.CARE, 40, 35, 50, 30, 30),
    },
)
BUILT_IN_JOBS: MappingProxyType[Job, BuiltInProfession] = partial(
    Job,
    {
        Job.FARMING: BuiltInProfession(PC.FOOD_PRODUCTION, 25, 25, 50, 25, 20),
        Job.HERDING: BuiltInProfession(PC.FOOD_PRODUCTION, 25, 25, 40, 30, 25),
        Job.FISHING: BuiltInProfession(PC.FOOD_PRODUCTION, 25, 25, 40, 40, 25),
        Job.MINING: BuiltInProfession(PC.EXTRACTION, 20, 30, 30, 60, 30),
        Job.CRAFTING: BuiltInProfession(PC.CRAFTING, 35, 35, 45, 30, 45),
        Job.TRADE: BuiltInProfession(PC.TRADE, 45, 60, 50, 15, 40),
        Job.SOLDIERING: BuiltInProfession(PC.WAR, 40, 30, 50, 60, 40),
        Job.CLERGY: BuiltInProfession(PC.FAITH, 60, 30, 70, 5, 50),
        Job.SCHOLARSHIP: BuiltInProfession(PC.LEARNING, 55, 35, 60, 5, 65),
        Job.BUILDING: BuiltInProfession(PC.BUILDING, 30, 35, 45, 45, 40),
        Job.SERVICE: BuiltInProfession(PC.SERVICE, 25, 25, 45, 10, 25),
    },
    without={Job.IDLE},
)
JOB_LABELS: dict[str, str] = {job.value: job.value.capitalize() for job in Job}
BUILT_IN_RANKS: MappingProxyType[SocialClass, BuiltInRank] = total(
    SocialClass,
    {
        SocialClass.FARMER: BuiltInRank(30, 20, 40, 30, 50),
        SocialClass.ARTISAN: BuiltInRank(40, 30, 35, 35, 50),
        SocialClass.MERCHANT: BuiltInRank(50, 40, 30, 45, 45),
        SocialClass.PRIEST: BuiltInRank(70, 55, 45, 15, 85),
        SocialClass.WARRIOR: BuiltInRank(55, 45, 55, 30, 45),
        SocialClass.SCRIBE: BuiltInRank(55, 40, 35, 35, 60),
        SocialClass.NOBLE: BuiltInRank(85, 75, 40, 10, 70),
        SocialClass.SERF_OR_SLAVE: BuiltInRank(10, 0, 80, 5, 30),
        SocialClass.OUTCAST: BuiltInRank(5, 0, 20, 10, 10),
        SocialClass.MONASTIC: BuiltInRank(55, 30, 50, 10, 85),
        SocialClass.WORKER: BuiltInRank(30, 20, 45, 35, 45),
        SocialClass.PROFESSIONAL: BuiltInRank(60, 45, 35, 45, 55),
        SocialClass.OFFICIAL: BuiltInRank(60, 50, 45, 30, 55),
        SocialClass.CITIZEN: BuiltInRank(50, 40, 35, 50, 50),
        SocialClass.UNEMPLOYED: BuiltInRank(15, 10, 10, 30, 40),
    },
)
BUILT_IN_ORGANISATIONS: MappingProxyType[FactionKind, BuiltInOrganisation] = total(
    FactionKind,
    {
        FactionKind.MERCHANT_GUILD: BuiltInOrganisation(OP.TRADE, OW.MEMBERS, OM.BY_TRADE, FS.ORGANISATION, OL.CHARTERED, OG.COUNCIL, 45, 55, 10),
        FactionKind.CRAFT_GUILD: BuiltInOrganisation(OP.CRAFT, OW.MEMBERS, OM.BY_TRADE, FS.ORGANISATION, OL.CHARTERED, OG.COUNCIL, 40, 60, 10),
        FactionKind.PRIESTHOOD: BuiltInOrganisation(OP.FAITH, OW.FAITH, OM.BY_OATH, FS.ORGANISATION, OL.CUSTOMARY, OG.HEREDITARY, 60, 65, 15),
        FactionKind.WARRIOR_ORDER: BuiltInOrganisation(OP.WAR, OW.MEMBERS, OM.BY_OATH, FS.COMPANY, OL.CUSTOMARY, OG.LEADER, 55, 70, 10),
        FactionKind.NOBLE_COUNCIL: BuiltInOrganisation(OP.RULE, OW.FOUNDER, OM.BY_BIRTH, FS.COMPANY, OL.CUSTOMARY, OG.COUNCIL, 70, 55, 10),
        FactionKind.PEASANT_LEAGUE: BuiltInOrganisation(OP.MUTUAL_AID, OW.MEMBERS, OM.OPEN, FS.NETWORK, OL.CUSTOMARY, OG.ASSEMBLY, 20, 45, 5),
        FactionKind.REBELS: BuiltInOrganisation(OP.POLITICS, OW.NONE, OM.BY_OATH, FS.BAND, OL.OUTLAWED, OG.LEADER, 25, 60, 50),
        FactionKind.BANDITS: BuiltInOrganisation(OP.CRIME, OW.NONE, OM.BY_POWER, FS.BAND, OL.OUTLAWED, OG.LEADER, 10, 45, 40),
        FactionKind.PIRATES: BuiltInOrganisation(OP.CRIME, OW.NONE, OM.BY_POWER, FS.BAND, OL.OUTLAWED, OG.LEADER, 15, 50, 35),
        FactionKind.ASSASSINS: BuiltInOrganisation(OP.CRIME, OW.FOUNDER, OM.BY_INVITATION, FS.BAND, OL.SECRET, OG.LEADER, 20, 70, 85),
        FactionKind.SCHOLARS_ACADEMY: BuiltInOrganisation(OP.LEARNING, OW.MEMBERS, OM.BY_INVITATION, FS.ORGANISATION, OL.CHARTERED, OG.COUNCIL, 60, 50, 5),
        FactionKind.SECRET_SOCIETY: BuiltInOrganisation(OP.SECRECY, OW.MEMBERS, OM.BY_INVITATION, FS.NETWORK, OL.SECRET, OG.COUNCIL, 30, 65, 90),
        FactionKind.MERCENARY_COMPANY: BuiltInOrganisation(OP.WAR, OW.FOUNDER, OM.BY_PURCHASE, FS.COMPANY, OL.LICENSED, OG.LEADER, 30, 55, 10),
        FactionKind.INTERWORLD_FEDERATION: BuiltInOrganisation(OP.POLITICS, OW.STATE, OM.BY_INVITATION, FS.NETWORK, OL.CHARTERED, OG.ASSEMBLY, 70, 45, 5),
        FactionKind.WANDERING_MARKET: BuiltInOrganisation(OP.TRADE, OW.MEMBERS, OM.OPEN, FS.NETWORK, OL.CUSTOMARY, OG.ASSEMBLY, 30, 40, 5),
        FactionKind.ROUTE_RAIDERS: BuiltInOrganisation(OP.CRIME, OW.NONE, OM.BY_POWER, FS.BAND, OL.OUTLAWED, OG.LEADER, 15, 50, 40),
        FactionKind.SOCIAL_CIRCLE: BuiltInOrganisation(OP.LEISURE, OW.MEMBERS, OM.BY_INVITATION, FS.BAND, OL.CUSTOMARY, OG.ASSEMBLY, 25, 50, 10),
        FactionKind.MAGE_ORDER: BuiltInOrganisation(OP.LEARNING, OW.MEMBERS, OM.BY_OATH, FS.ORGANISATION, OL.LICENSED, OG.COUNCIL, 55, 60, 40, foundable=False),
        FactionKind.ESTATE: BuiltInOrganisation(OP.RULE, OW.MEMBERS, OM.BY_BIRTH, FS.ORGANISATION, OL.CUSTOMARY, OG.ASSEMBLY, 50, 50, 5, foundable=False),
        FactionKind.PARTY: BuiltInOrganisation(OP.POLITICS, OW.MEMBERS, OM.OPEN, FS.ORGANISATION, OL.LICENSED, OG.COUNCIL, 40, 45, 5, foundable=False),
        FactionKind.MOVEMENT: BuiltInOrganisation(OP.POLITICS, OW.NONE, OM.OPEN, FS.NETWORK, OL.CUSTOMARY, OG.ASSEMBLY, 30, 40, 10, foundable=False),
        FactionKind.CHARTERED_COMPANY: BuiltInOrganisation(
            OP.TRADE, OW.SHAREHOLDERS, OM.BY_PURCHASE, FS.ORGANISATION, OL.CHARTERED, OG.COUNCIL, 55, 50, 10, foundable=False
        ),
        FactionKind.HOLY_ORDER: BuiltInOrganisation(OP.FAITH, OW.FAITH, OM.BY_OATH, FS.ORGANISATION, OL.CUSTOMARY, OG.LEADER, 60, 70, 20, foundable=False),
        FactionKind.CRIME_FAMILY: BuiltInOrganisation(OP.CRIME, OW.FOUNDER, OM.BY_BIRTH, FS.COMPANY, OL.SECRET, OG.HEREDITARY, 20, 75, 80),
        FactionKind.THIEVES_GUILD: BuiltInOrganisation(OP.CRIME, OW.MEMBERS, OM.BY_INVITATION, FS.COMPANY, OL.SECRET, OG.COUNCIL, 15, 60, 75),
        FactionKind.SMUGGLING_RING: BuiltInOrganisation(OP.CRIME, OW.MEMBERS, OM.BY_INVITATION, FS.BAND, OL.SECRET, OG.LEADER, 15, 55, 70),
        FactionKind.PIRATE_CONFEDERACY: BuiltInOrganisation(OP.CRIME, OW.MEMBERS, OM.BY_POWER, FS.NETWORK, OL.OUTLAWED, OG.COUNCIL, 20, 45, 30),
        FactionKind.ART_MOVEMENT: BuiltInOrganisation(OP.LEISURE, OW.NONE, OM.OPEN, FS.NETWORK, OL.CUSTOMARY, OG.ASSEMBLY, 35, 40, 5, foundable=False),
        FactionKind.CLUB: BuiltInOrganisation(OP.LEISURE, OW.MEMBERS, OM.BY_PURCHASE, FS.BAND, OL.LICENSED, OG.COUNCIL, 30, 45, 5, foundable=False),
        FactionKind.LEAGUE: BuiltInOrganisation(OP.LEISURE, OW.MEMBERS, OM.OPEN, FS.ORGANISATION, OL.LICENSED, OG.COUNCIL, 35, 45, 5, foundable=False),
        FactionKind.WORKERS_UNION: BuiltInOrganisation(OP.MUTUAL_AID, OW.MEMBERS, OM.BY_TRADE, FS.ORGANISATION, OL.LICENSED, OG.ASSEMBLY, 30, 60, 10),
        FactionKind.ENGINEERS_SOCIETY: BuiltInOrganisation(OP.MAKING, OW.MEMBERS, OM.BY_TRADE, FS.ORGANISATION, OL.CHARTERED, OG.COUNCIL, 50, 50, 5),
        FactionKind.FINANCIERS: BuiltInOrganisation(OP.TRADE, OW.SHAREHOLDERS, OM.BY_PURCHASE, FS.COMPANY, OL.CHARTERED, OG.COUNCIL, 55, 45, 30),
        FactionKind.VETERANS: BuiltInOrganisation(OP.MUTUAL_AID, OW.MEMBERS, OM.BY_TRADE, FS.NETWORK, OL.CUSTOMARY, OG.COUNCIL, 35, 60, 5),
    },
)

PROFESSION_CATEGORY_LABELS: dict[str, str] = {
    "food_production": "Food production",
    "crafting": "Crafting",
    "trade": "Trade",
    "transport": "Transport",
    "care": "Care",
    "healing": "Healing",
    "learning": "Learning",
    "faith": "Faith",
    "rule_and_administration": "Rule and administration",
    "law": "Law",
    "war": "War",
    "security": "Security",
    "art_and_entertainment": "Art and entertainment",
    "service": "Service",
    "building": "Building",
    "extraction": "Extraction",
    "science_and_engineering": "Science and engineering",
    "information": "Information",
    "making_minds": "Making minds",
    "living_craft": "Living craft",
    "magic": "Magic",
    "exploration": "Exploration",
}
PROFESSION_BASE_LABELS = spoken_labels(Profession)
CLASS_LABELS: dict[str, str] = {
    "farmer": "Farmer",
    "artisan": "Artisan",
    "merchant": "Merchant",
    "priest": "Priest",
    "warrior": "Warrior",
    "scribe": "Scribe",
    "noble": "Noble",
    "serf_or_slave": "Bonded",
    "outcast": "Outcast",
    "monastic": "Monastic",
    "worker": "Worker",
    "professional": "Professional",
    "official": "Official",
    "citizen": "Citizen",
    "unemployed": "Unemployed",
}
PURPOSE_LABELS: dict[str, str] = {
    "trade": "Trade",
    "craft": "Craft",
    "faith": "Faith",
    "war": "War",
    "learning": "Learning",
    "rule": "Rule",
    "crime": "Crime",
    "mutual_aid": "Mutual aid",
    "leisure": "Leisure",
    "secrecy": "Secrecy",
    "politics": "Politics",
    "exploration": "Exploration",
    "making": "Making",
    "care": "Care",
}
OWNERSHIP_LABELS: dict[str, str] = {
    "members": "Its members",
    "shareholders": "Shareholders",
    "founder": "Its founder",
    "state": "The state",
    "faith": "A faith",
    "none": "No one",
}
MEMBERSHIP_LABELS: dict[str, str] = {
    "open": "Open to all",
    "by_trade": "By trade",
    "by_birth": "By birth",
    "by_oath": "By oath",
    "by_invitation": "By invitation",
    "by_purchase": "By purchase",
    "by_power": "By strength",
}
SCALE_LABELS: dict[str, str] = {
    "band": "Band",
    "company": "Company",
    "organisation": "Organisation",
    "network": "Network",
}
LEGAL_LABELS: dict[str, str] = {
    "chartered": "Chartered",
    "licensed": "Licensed",
    "customary": "Customary",
    "outlawed": "Outlawed",
    "secret": "Secret",
}
GOVERNANCE_LABELS: dict[str, str] = {
    "leader": "A single leader",
    "council": "Council",
    "assembly": "Assembly",
    "hereditary": "Passed by descent",
    "made_mind": "A made mind",
}
ORGANISATION_BASE_LABELS: dict[str, str] = {
    "merchant_guild": "Merchant guild",
    "craft_guild": "Craft guild",
    "priesthood": "Priesthood",
    "warrior_order": "Warrior order",
    "noble_council": "Noble council",
    "peasant_league": "Peasant league",
    "rebels": "Rebels",
    "bandits": "Bandits",
    "pirates": "Pirates",
    "assassins": "Assassins",
    "scholars_academy": "Scholars academy",
    "secret_society": "Secret society",
    "mercenary_company": "Mercenary company",
    "interworld_federation": "Interworld federation",
    "wandering_market": "Wandering market",
    "route_raiders": "Route raiders",
    "social_circle": "Social circle",
    "mage_order": "Mage order",
    "estate": "Estate",
    "party": "Party",
    "movement": "Movement",
    "chartered_company": "Chartered company",
    "holy_order": "Holy order",
    "crime_family": "Crime family",
    "thieves_guild": "Thieves guild",
    "smuggling_ring": "Smuggling ring",
    "pirate_confederacy": "Pirate confederacy",
    "art_movement": "Art movement",
    "club": "Club",
    "league": "League",
    "workers_union": "Workers union",
    "engineers_society": "Engineers society",
    "financiers": "Financiers",
    "veterans": "Veterans",
}

PROFESSION_SPEC = ConceptSpec(
    concept=KindConcept.PROFESSION,
    label="Profession",
    plural="Professions",
    hint="Kinds of work a people does, each with its standing, earnings and risks",
    table=ProfessionKindRow,
    category=ProfessionCategory,
    category_labels=PROFESSION_CATEGORY_LABELS,
    properties=(
        KindProperty("base", "Work it does", "The profession of the world it stands for", options=PROFESSION_BASE_LABELS),
        KindProperty("job", "Work of the many", "The kind of work of the common folk it stands for", options=JOB_LABELS),
        KindProperty("prestige", "Prestige", "Standing it lends; raises how fast it spreads"),
        KindProperty("income", "Earnings", "What it brings to the towns where it is held"),
        KindProperty("purity", "Purity", "How clean the work is held to be; the least pure sink to the lowest rank"),
        KindProperty("mishap_exposure", "Risk", "How often the work hurts those who do it"),
        KindProperty("skill_need", "Skill needed", "How much skill it takes"),
    ),
    readers=("society_kinds", "purity", "ways_of_life"),
)
RANK_SPEC = ConceptSpec(
    concept=KindConcept.RANK,
    label="Rank",
    plural="Ranks",
    hint="Ranks a people sets over its classes, with their privileges and duties",
    table=RankKindRow,
    category=SocialClass,
    category_labels=CLASS_LABELS,
    properties=(
        KindProperty("standing", "Standing", "How high the rank stands"),
        KindProperty("privilege", "Privilege", "What the rank may claim; raises the class's contentment"),
        KindProperty("duty", "Duty", "What the rank owes; weighs on the class's contentment"),
        KindProperty("mobility", "Mobility", "How easily one rises out of it or into it"),
        KindProperty("purity", "Purity", "How clean the rank is held to be"),
    ),
    readers=("society_kinds", "ways_of_life"),
)
FOUNDABLE_LABELS: dict[str, str] = {"True": "Mortals may found it", "False": "It arises only by other means"}

ORGANISATION_SPEC = ConceptSpec(
    concept=KindConcept.ORGANISATION,
    label="Organisation",
    plural="Organisations",
    hint="Kinds of bodies people found, set by purpose, ownership, membership and law",
    table=OrganisationKindRow,
    category=OrganisationPurpose,
    category_labels=PURPOSE_LABELS,
    properties=(
        KindProperty("base", "Body it stands for", "The kind of faction in the world it shapes", options=ORGANISATION_BASE_LABELS),
        KindProperty("ownership", "Owned by", "Who owns it", options=OWNERSHIP_LABELS),
        KindProperty("membership", "Joined", "How one joins it", options=MEMBERSHIP_LABELS),
        KindProperty("scale", "Scale", "How large it grows", options=SCALE_LABELS),
        KindProperty("legal_form", "Standing in law", "How the law holds it; an outlawed body is hunted", options=LEGAL_LABELS),
        KindProperty("governance", "Led by", "How it is led", options=GOVERNANCE_LABELS),
        KindProperty("prestige", "Prestige", "Repute it lends its factions"),
        KindProperty("cohesion", "Cohesion", "How firmly its members hold together"),
        KindProperty("secrecy", "Secrecy", "How hidden its factions keep"),
        KindProperty("foundable", "Founded by mortals", "Whether a mortal may found a body of this kind", options=FOUNDABLE_LABELS),
    ),
    readers=("society_kinds", "ways_of_life"),
)
SPECS = (PROFESSION_SPEC, RANK_SPEC, ORGANISATION_SPEC)
