from enum import StrEnum


class SelectorateKind(StrEnum):
    TRIBE = "tribe"
    NOBLES = "nobles"
    COUNCIL = "council"
    ARMY = "army"
    PRIESTS = "priests"
    CITIZENS = "citizens"
    PARTY = "party"
    SHAREHOLDERS = "shareholders"
    ALGORITHM = "algorithm"


class LegitimacyType(StrEnum):
    TRADITIONAL = "traditional"
    CHARISMATIC = "charismatic"
    RATIONAL = "rational"
    DIVINE_MANDATE = "divine_mandate"
    POPULAR = "popular"
    PERFORMANCE = "performance"


class Routinisation(StrEnum):
    NONE = "none"
    PENDING = "pending"
    DYNASTY = "dynasty"
    INSTITUTION = "institution"
    SCHISM = "schism"


class LeadershipMode(StrEnum):
    ACHIEVED = "achieved"
    ASCRIBED = "ascribed"
    STATE = "state"


class ClientRole(StrEnum):
    HOUSEHOLD = "household"
    RETAINER = "retainer"
    OFFICIAL = "official"
    COMMANDER = "commander"


class PowerStance(StrEnum):
    LOYAL = "loyal"
    DEFIANT = "defiant"
    EXTORTING = "extorting"
    PLOTTING = "plotting"


class SegmentLevel(StrEnum):
    LINEAGE = "lineage"
    CLAN = "clan"
    TRIBE = "tribe"


class CredentialKind(StrEnum):
    EXAMINATION = "examination"
    MASTER = "master"
    DOCTOR = "doctor"
    ORDINATION = "ordination"
    DEGREE = "degree"
    LICENCE = "licence"
    COMMISSION = "commission"
