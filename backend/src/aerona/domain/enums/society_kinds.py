from enum import StrEnum


class ProfessionCategory(StrEnum):
    FOOD_PRODUCTION = "food_production"
    CRAFTING = "crafting"
    TRADE = "trade"
    TRANSPORT = "transport"
    CARE = "care"
    HEALING = "healing"
    LEARNING = "learning"
    FAITH = "faith"
    RULE_AND_ADMINISTRATION = "rule_and_administration"
    LAW = "law"
    WAR = "war"
    SECURITY = "security"
    ART_AND_ENTERTAINMENT = "art_and_entertainment"
    SERVICE = "service"
    BUILDING = "building"
    EXTRACTION = "extraction"
    SCIENCE_AND_ENGINEERING = "science_and_engineering"
    INFORMATION = "information"
    MAKING_MINDS = "making_minds"
    LIVING_CRAFT = "living_craft"
    MAGIC = "magic"
    EXPLORATION = "exploration"


class OrganisationPurpose(StrEnum):
    TRADE = "trade"
    CRAFT = "craft"
    FAITH = "faith"
    WAR = "war"
    LEARNING = "learning"
    RULE = "rule"
    CRIME = "crime"
    MUTUAL_AID = "mutual_aid"
    LEISURE = "leisure"
    SECRECY = "secrecy"
    POLITICS = "politics"
    EXPLORATION = "exploration"
    MAKING = "making"
    CARE = "care"


class OrganisationOwnership(StrEnum):
    MEMBERS = "members"
    SHAREHOLDERS = "shareholders"
    FOUNDER = "founder"
    STATE = "state"
    FAITH = "faith"
    NONE = "none"


class OrganisationMembership(StrEnum):
    OPEN = "open"
    BY_TRADE = "by_trade"
    BY_BIRTH = "by_birth"
    BY_OATH = "by_oath"
    BY_INVITATION = "by_invitation"
    BY_PURCHASE = "by_purchase"
    BY_POWER = "by_power"


class OrganisationLegalForm(StrEnum):
    CHARTERED = "chartered"
    LICENSED = "licensed"
    CUSTOMARY = "customary"
    OUTLAWED = "outlawed"
    SECRET = "secret"


class OrganisationGovernance(StrEnum):
    LEADER = "leader"
    COUNCIL = "council"
    ASSEMBLY = "assembly"
    HEREDITARY = "hereditary"
    MADE_MIND = "made_mind"
