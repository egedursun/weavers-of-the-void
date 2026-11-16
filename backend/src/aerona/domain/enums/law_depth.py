from enum import StrEnum


class LegalSystem(StrEnum):
    CUSTOMARY = "customary"
    CODIFIED = "codified"
    RELIGIOUS = "religious"
    PRECEDENT = "precedent"
    ORACLE = "oracle"
    MIXED = "mixed"


class CourtLevel(StrEnum):
    LOCAL = "local"
    PROVINCIAL = "provincial"
    HIGH = "high"
    RELIGIOUS = "religious"


class RegistryKind(StrEnum):
    LAND_TITLE = "land_title"
    DEBT = "debt"
    SALE = "sale"
    DOWRY = "dowry"
    INDENTURE = "indenture"
    PATENT = "patent"
    PATTERN = "pattern"
    MIND_STATE = "mind_state"
    LINE = "line"
    COMPANY = "company"
    BIRTH = "birth"
    DEATH = "death"
    CITIZENSHIP = "citizenship"


class JurisdictionClaim(StrEnum):
    CLERGY = "clergy"
    GUILD = "guild"
    FOREIGN = "foreign"


class RecruitMotive(StrEnum):
    MONEY = "money"
    IDEOLOGY = "ideology"
    COMPROMISE = "compromise"
    EGO = "ego"


class MoleHuntOutcome(StrEnum):
    CAUGHT = "caught"
    CLEARED = "cleared"
    PURGED = "purged"
    DEFECTED = "defected"


class KillMethod(StrEnum):
    BLADE = "blade"
    POISON = "poison"
    ACCIDENT = "accident"
    DISEASE = "disease"
    CURSE = "curse"
