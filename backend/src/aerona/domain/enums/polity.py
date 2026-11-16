from enum import StrEnum


class GovernmentKind(StrEnum):
    CHIEFDOM = "chiefdom"
    MONARCHY = "monarchy"
    THEOCRACY = "theocracy"
    OLIGARCHY = "oligarchy"
    REPUBLIC = "republic"
    TRIBAL_CONFEDERATION = "tribal_confederation"
    EMPIRE = "empire"
    HIVE_COUNCIL = "hive_council"
    GOD_KINGDOM = "god_kingdom"
    OCCUPATION = "occupation"
    JUNTA = "junta"
    CORPORATE_STATE = "corporate_state"
    TECHNOCRACY = "technocracy"
    FEDERATION = "federation"
    COMMUNE = "commune"
    MACHINE_RULE = "machine_rule"
    COLONIAL_ADMINISTRATION = "colonial_administration"


class DecisionRule(StrEnum):
    AUTOCRATIC = "autocratic"
    COUNCIL = "council"
    ASSEMBLY = "assembly"
    DIVINE = "divine"


class OfficeKind(StrEnum):
    RULER = "ruler"
    HEIR_DESIGNATE = "heir_designate"
    REGENT = "regent"
    CHANCELLOR = "chancellor"
    MARSHAL = "marshal"
    TREASURER = "treasurer"
    HIGH_JUDGE = "high_judge"
    SPYMASTER = "spymaster"
    GOVERNOR = "governor"
    AMBASSADOR = "ambassador"
    HERALD = "herald"
    CHAPLAIN = "chaplain"
    COURT_SCHOLAR = "court_scholar"
    HEAD_OF_STATE = "head_of_state"
    HEAD_OF_GOVERNMENT = "head_of_government"
    MINISTER = "minister"
    GENERAL = "general"
    ADMIRAL = "admiral"
    SPEAKER = "speaker"
    CHIEF_SCIENTIST = "chief_scientist"
    JESTER = "jester"
    WARDEN = "warden"


class OfficePower(StrEnum):
    RULE = "rule"
    SUCCEED = "succeed"
    NEGOTIATE = "negotiate"
    COMMAND = "command"
    TREASURY = "treasury"
    JUDGE = "judge"
    SPY = "spy"
    GOVERN = "govern"
    EMBASSY = "embassy"
    PROCLAIM = "proclaim"
    PREACH = "preach"
    RESEARCH = "research"
    JEST = "jest"


class RegionalStanding(StrEnum):
    HEGEMON = "hegemon"
    GREAT_POWER = "great_power"
    MINOR_POWER = "minor_power"
    CLIENT = "client"


class RevoltKind(StrEnum):
    PEASANT = "peasant"
    NOBLE = "noble"
    RELIGIOUS = "religious"
    SECESSION = "secession"
    SLAVE = "slave"


class SuccessionRule(StrEnum):
    PRIMOGENITURE = "primogeniture"
    SENIORITY = "seniority"
    ELECTIVE = "elective"
    TANISTRY = "tanistry"
    MATRILINEAL = "matrilineal"
    BY_COMBAT = "by_combat"
    DIVINE_CHOICE = "divine_choice"
    ULTIMOGENITURE = "ultimogeniture"


class GenderRule(StrEnum):
    ANY = "any"
    MALE_PREFERENCE = "male_preference"
    MALE_ONLY = "male_only"
    FEMALE_PREFERENCE = "female_preference"
    FEMALE_ONLY = "female_only"


class LawArea(StrEnum):
    SUCCESSION = "succession"
    PROPERTY = "property"
    FISCAL = "fiscal"
    PENAL = "penal"
    MILITARY = "military"
    SOCIAL = "social"
    PUBLIC_HEALTH = "public_health"
    MAGIC = "magic"
    CONSTITUTIONAL = "constitutional"


class LawKind(StrEnum):
    SUCCESSION_RULE = "succession_rule"
    INHERITANCE_SPLIT = "inheritance_split"
    LAND_TENURE = "land_tenure"
    SLAVERY = "slavery"
    SERFDOM = "serfdom"
    TAX_RATE = "tax_rate"
    TITHE = "tithe"
    TOLLS = "tolls"
    DEBT_LAW = "debt_law"
    PENAL_CODE = "penal_code"
    LEVY_LAW = "levy_law"
    CONSCRIPTION = "conscription"
    STANDING_ARMY = "standing_army"
    VETERAN_PENSION = "veteran_pension"
    RANSOM_CUSTOM = "ransom_custom"
    MARRIAGE_LAW = "marriage_law"
    SUMPTUARY = "sumptuary"
    GUILD_CHARTER = "guild_charter"
    FOREIGNER_RIGHTS = "foreigner_rights"
    RELIGIOUS_TOLERANCE = "religious_tolerance"
    WORSHIP_BAN = "worship_ban"
    CENSORSHIP = "censorship"
    BLOOD_FEUD = "blood_feud"
    QUARANTINE = "quarantine"
    BURIAL_LAW = "burial_law"
    SANITATION = "sanitation"
    FAIR_MARKET = "fair_market"
    MAGIC_BAN = "magic_ban"
    LICENSED_MAGIC = "licensed_magic"
    RITE_RESTRICTIONS = "rite_restrictions"
    FRANCHISE = "franchise"
    CONSTITUTION = "constitution"
    CUSTOM = "custom"
    LABOUR_LAW = "labour_law"
    ENVIRONMENT_LAW = "environment_law"
    DATA_PRIVACY = "data_privacy"
    WEAPONS_LAW = "weapons_law"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    MACHINE_LAW = "machine_law"
    SPACE_LAW = "space_law"
    CLOSED_SEASON = "closed_season"
    PROTECTED_WATERS = "protected_waters"
    CATCH_QUOTA = "catch_quota"
    GEAR_BAN = "gear_ban"


class DebtRemedy(StrEnum):
    BONDAGE = "bondage"
    PRISON = "prison"
    JUBILEE = "jubilee"


class LegitimacyBasis(StrEnum):
    CUSTOM = "custom"
    DECREE = "decree"
    DIVINE = "divine"
    COUNCIL = "council"


class Jurisdiction(StrEnum):
    POLITY = "polity"
    SETTLEMENT = "settlement"
    CULT = "cult"


class ClaimBasis(StrEnum):
    INHERITANCE = "inheritance"
    MARRIAGE = "marriage"
    CONQUEST = "conquest"
    DIVINE = "divine"
    FABRICATED = "fabricated"
    DE_JURE = "de_jure"


class HouseTrait(StrEnum):
    LONG_LIVED = "long_lived"
    GIANT_BLOODED = "giant_blooded"
    GOD_BLOODED = "god_blooded"
    CURSED = "cursed"
    FERTILE = "fertile"
    SEER_GIFT = "seer_gift"


class OathKind(StrEnum):
    FEALTY = "fealty"
    VENGEANCE = "vengeance"
    CELIBACY = "celibacy"
    PILGRIMAGE = "pilgrimage"
    PROTECTION = "protection"
    SILENCE = "silence"
    SWORN_KINSHIP = "sworn_kinship"


class OathStatus(StrEnum):
    SWORN = "sworn"
    KEPT = "kept"
    BROKEN = "broken"
    FULFILLED = "fulfilled"


class TreatyKind(StrEnum):
    PEACE = "peace"
    TRUCE = "truce"
    ALLIANCE_DEFENSIVE = "alliance_defensive"
    ALLIANCE_OFFENSIVE = "alliance_offensive"
    NON_AGGRESSION = "non_aggression"
    VASSALAGE = "vassalage"
    TRIBUTE = "tribute"
    MARRIAGE_PACT = "marriage_pact"
    TRADE_PACT = "trade_pact"
    CONDOTTA = "condotta"
    GUARANTEE = "guarantee"
    INTERWORLD = "interworld"
    COALITION = "coalition"
    DIVINE_PACT = "divine_pact"
    NAVAL_LIMIT = "naval_limit"


class TreatyStatus(StrEnum):
    IN_FORCE = "in_force"
    FULFILLED = "fulfilled"
    BROKEN = "broken"
    EXPIRED = "expired"
    PROPOSED = "proposed"
    REJECTED = "rejected"


class ClauseKind(StrEnum):
    CALL_TO_ARMS = "call_to_arms"
    TRIBUTE = "tribute"
    CESSION = "cession"
    HOSTAGE = "hostage"
    MARRIAGE = "marriage"
    TRADE_RIGHTS = "trade_rights"
    TOLLS_WAIVED = "tolls_waived"
    RELIGIOUS_FREEDOM = "religious_freedom"
    DEMILITARISED = "demilitarised"
    CHAMPION = "champion"
    EXTRADITION = "extradition"
    WERGILD = "wergild"
    NON_AGGRESSION = "non_aggression"
    ROUTE_CONTROL = "route_control"
    RESOURCE_DEMAND = "resource_demand"
    RESEARCH_AGREEMENT = "research_agreement"
    FLEET_LIMIT = "fleet_limit"


class PartyRole(StrEnum):
    SIGNATORY = "signatory"
    OVERLORD = "overlord"
    VASSAL = "vassal"
    GUARANTOR = "guarantor"


CLOSURES = frozenset({LawKind.CLOSED_SEASON, LawKind.PROTECTED_WATERS, LawKind.CATCH_QUOTA, LawKind.GEAR_BAN})

LAW_AREAS: dict[LawKind, LawArea] = {
    LawKind.SUCCESSION_RULE: LawArea.SUCCESSION,
    LawKind.INHERITANCE_SPLIT: LawArea.PROPERTY,
    LawKind.LAND_TENURE: LawArea.PROPERTY,
    LawKind.SLAVERY: LawArea.PROPERTY,
    LawKind.SERFDOM: LawArea.PROPERTY,
    LawKind.TAX_RATE: LawArea.FISCAL,
    LawKind.TITHE: LawArea.FISCAL,
    LawKind.TOLLS: LawArea.FISCAL,
    LawKind.DEBT_LAW: LawArea.FISCAL,
    LawKind.PENAL_CODE: LawArea.PENAL,
    LawKind.LEVY_LAW: LawArea.MILITARY,
    LawKind.CONSCRIPTION: LawArea.MILITARY,
    LawKind.STANDING_ARMY: LawArea.MILITARY,
    LawKind.VETERAN_PENSION: LawArea.MILITARY,
    LawKind.RANSOM_CUSTOM: LawArea.MILITARY,
    LawKind.MARRIAGE_LAW: LawArea.SOCIAL,
    LawKind.SUMPTUARY: LawArea.SOCIAL,
    LawKind.GUILD_CHARTER: LawArea.SOCIAL,
    LawKind.FOREIGNER_RIGHTS: LawArea.SOCIAL,
    LawKind.RELIGIOUS_TOLERANCE: LawArea.SOCIAL,
    LawKind.WORSHIP_BAN: LawArea.SOCIAL,
    LawKind.BLOOD_FEUD: LawArea.SOCIAL,
    LawKind.QUARANTINE: LawArea.PUBLIC_HEALTH,
    LawKind.BURIAL_LAW: LawArea.PUBLIC_HEALTH,
    LawKind.SANITATION: LawArea.PUBLIC_HEALTH,
    LawKind.FAIR_MARKET: LawArea.FISCAL,
    LawKind.MAGIC_BAN: LawArea.MAGIC,
    LawKind.LICENSED_MAGIC: LawArea.MAGIC,
    LawKind.RITE_RESTRICTIONS: LawArea.MAGIC,
    LawKind.CENSORSHIP: LawArea.SOCIAL,
    LawKind.FRANCHISE: LawArea.CONSTITUTIONAL,
    LawKind.CONSTITUTION: LawArea.CONSTITUTIONAL,
    LawKind.CUSTOM: LawArea.SOCIAL,
    LawKind.LABOUR_LAW: LawArea.SOCIAL,
    LawKind.ENVIRONMENT_LAW: LawArea.PUBLIC_HEALTH,
    LawKind.DATA_PRIVACY: LawArea.SOCIAL,
    LawKind.CLOSED_SEASON: LawArea.PROPERTY,
    LawKind.PROTECTED_WATERS: LawArea.PROPERTY,
    LawKind.CATCH_QUOTA: LawArea.PROPERTY,
    LawKind.GEAR_BAN: LawArea.PROPERTY,
    LawKind.WEAPONS_LAW: LawArea.PENAL,
    LawKind.INTELLECTUAL_PROPERTY: LawArea.PROPERTY,
    LawKind.MACHINE_LAW: LawArea.SOCIAL,
    LawKind.SPACE_LAW: LawArea.PROPERTY,
}
