from enum import StrEnum


class SubjectKind(StrEnum):
    VASSAL = "vassal"
    TRIBUTARY = "tributary"
    MARCH = "march"
    PERSONAL_UNION = "personal_union"
    CLIENT = "client"
    COLONY = "colony"
    PROTECTORATE = "protectorate"
    ENCLAVE = "enclave"
    MANDATE = "mandate"
    ASSOCIATED_STATE = "associated_state"


class CrisisDemand(StrEnum):
    CEDE_REGION = "cede_region"
    RELEASE_VASSAL = "release_vassal"
    CONVERT = "convert"
    PAY = "pay"


class CrisisState(StrEnum):
    ESCALATING = "escalating"
    BACKED_DOWN = "backed_down"
    CONCEDED = "conceded"
    WAR = "war"


class CrisisSide(StrEnum):
    DEMANDER = "demander"
    TARGET = "target"


class CouncilTask(StrEnum):
    IMPROVE_RELATIONS = "improve_relations"
    TRAIN_TROOPS = "train_troops"
    COLLECT_TAXES = "collect_taxes"
    DISRUPT_SCHEMES = "disrupt_schemes"
    CONVERT_PROVINCE = "convert_province"
    PURGE_CORRUPTION = "purge_corruption"


class TaxKind(StrEnum):
    LAND = "land"
    POLL = "poll"
    TRADE = "trade"
    CONSUMPTION = "consumption"
    TITHE = "tithe"
    INCOME = "income"
    PROPERTY = "property"
    INHERITANCE = "inheritance"
    WEALTH = "wealth"
    COMPANY = "company"
    LABOUR_LEVY = "labour_levy"
    IN_KIND = "in_kind"
    LICENCE = "licence"
    SEIGNIORAGE = "seigniorage"
    POLLUTION = "pollution"
    EXCISE = "excise"


class MandateKind(StrEnum):
    PRODUCE = "produce"
    EXPORT_BAN = "export_ban"
    BUILD = "build"
    FAMINE_RELIEF = "famine_relief"
    CURFEW = "curfew"
    SLUM_CLEARANCE = "slum_clearance"
    PREPARE = "prepare"
    ENCLOSURE = "enclosure"


class MandateState(StrEnum):
    ACTIVE = "active"
    MET = "met"
    FAILED = "failed"


class NobleWant(StrEnum):
    DWELLING = "dwelling"
    FINE_GOODS = "fine_goods"
    OFFICE = "office"
    HONOUR = "honour"


class ResolutionKind(StrEnum):
    ROUTE_SECURITY = "route_security"
    EMBARGO = "embargo"
    VOID_BAN = "void_ban"
    SANCTION = "sanction"


class ResolutionState(StrEnum):
    PROPOSED = "proposed"
    PASSED = "passed"
    REJECTED = "rejected"
    LAPSED = "lapsed"


class CourtPosition(StrEnum):
    STEWARD = "steward"
    CHAMPION = "champion"
    PHYSICIAN = "physician"
    TUTOR = "tutor"
    CHRONICLER = "chronicler"
    MASTER_OF_REVELS = "master_of_revels"
