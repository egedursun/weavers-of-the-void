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
    GOD_REALM = "god_realm"
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
    WORKER = "worker"
    URBAN = "urban"
    MUTINY = "mutiny"
    MINORITY = "minority"
    COLONIAL = "colonial"
    TAX = "tax"
    SUCCESSION = "succession"
    SCHOLAR = "scholar"
    MADE_MINDS = "made_minds"
    GIFTED = "gifted"


class SuccessionRule(StrEnum):
    PRIMOGENITURE = "primogeniture"
    SENIORITY = "seniority"
    ELECTIVE = "elective"
    TANISTRY = "tanistry"
    THROUGH_SECOND_LINE = "through_second_line"
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
    MIND_STATUS = "mind_status"
    COPY_LAW = "copy_law"
    COPY_SUCCESSION = "copy_succession"
    ERASURE_LAW = "erasure_law"
    AUGMENT_LAW = "augment_law"
    NETWORK_LAW = "network_law"
    SURVEILLANCE_LAW = "surveillance_law"
    PROVISION_LAW = "provision_law"
    POWER_LAW = "power_law"
    SOURCE_LAW = "source_law"
    LIVING_CRAFT_LAW = "living_craft_law"
    CLONE_LAW = "clone_law"
    CLONE_STATUS = "clone_status"
    GERMLINE_LAW = "germline_law"
    DESIGNED_STATUS = "designed_status"


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
    STRONG_BLOODED = "strong_blooded"
    SWIFT = "swift"
    QUICK_HEALING = "quick_healing"
    SHARP_SENSED = "sharp_sensed"
    STEADY = "steady"
    QUICK_MINDED = "quick_minded"


class OathKind(StrEnum):
    FEALTY = "fealty"
    VENGEANCE = "vengeance"
    CELIBACY = "celibacy"
    PILGRIMAGE = "pilgrimage"
    PROTECTION = "protection"
    SILENCE = "silence"
    SWORN_KINSHIP = "sworn_kinship"
    SERVICE = "service"
    POVERTY = "poverty"
    NONVIOLENCE = "nonviolence"
    FIDELITY = "fidelity"
    SECRECY = "secrecy"


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


class InterworldTreatyKind(StrEnum):
    ALLIANCE = "alliance"
    TRADE = "trade"


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
    AUTONOMOUS_WEAPONS_BAN = "autonomous_weapons_ban"
    MIND_SEIZURE_BAN = "mind_seizure_ban"
    SOLDIER_COPY_BAN = "soldier_copy_ban"
    REPLICATOR_WEAPON_BAN = "replicator_weapon_ban"
    CIVIL_NETWORK_SHIELD = "civil_network_shield"
    CIVIL_HOST_SHIELD = "civil_host_shield"
    NO_MIND_COMPULSION = "no_mind_compulsion"
    NO_PLAGUE_POWERS = "no_plague_powers"
    NO_DESIGNED_DISEASE = "no_designed_disease"


class PartyRole(StrEnum):
    SIGNATORY = "signatory"
    OVERLORD = "overlord"
    VASSAL = "vassal"
    GUARANTOR = "guarantor"


CLOSURES = frozenset({LawKind.CLOSED_SEASON, LawKind.PROTECTED_WATERS, LawKind.CATCH_QUOTA, LawKind.GEAR_BAN})


class OathPenalty(StrEnum):
    SHAME = "shame"
    FINE = "fine"
    EXILE = "exile"
    OUTLAWRY = "outlawry"
    CURSE = "curse"


class OathBreach(StrEnum):
    BLOOD_UNAVENGED = "the_blood_went_unavenged"
    ROAD_UNWALKED = "the_road_was_never_walked"
    SERVICE_LEFT = "the_service_was_left"
    WEALTH_GATHERED = "wealth_was_gathered"
    BLOOD_SHED = "blood_was_shed"
    UNION_PUT_ASIDE = "the_union_was_put_aside"
    KEEPERS_LEFT = "the_keepers_were_left"
    LOVER_TAKEN = "a_lover_was_taken"
    THRONE_SEIZED = "the_throne_was_seized"
    MEMBER_BROKE_AWAY = "a_member_broke_away"
    TOWN_REVOLTED = "a_town_rose_in_revolt"
    SECRETS_TOLD = "secrets_were_told"
    SECRETS_WRUNG = "secrets_were_wrung_out"
    MARRIAGE_MADE = "a_marriage_was_made"
    GOD_RELEASED = "a_god_broke_it"
    TREATY_BROKEN = "the_treaty_was_broken"


class TreatyBreach(StrEnum):
    WAR_ON_PARTY = "war_on_a_sworn_party"
    CLAUSE_MISREAD = "a_misread_clause"
    SOLDIERS_IN_DEMILITARISED_LAND = "soldiers_in_demilitarised_land"
    FLEET_PAST_TONNAGE = "a_fleet_past_its_tonnage"
    FORBIDDEN_METHOD = "a_forbidden_method_of_war"
    TRIBUTE_UNPAID = "tribute_left_unpaid"
    HOSTAGE_TAKEN_BACK = "a_hostage_taken_back"
    TOLLS_CHARGED = "tolls_charged"
    SUBMITTED_TO_ANOTHER = "submission_to_another_overlord"
    ROSE_AGAINST_OVERLORD = "a_rising_against_the_overlord"
    HIDDEN_SHOWN = "what_was_hidden_shown"
    GOD_COMMANDED = "a_god_commanded_it"
    CALL_TO_ARMS_REFUSED = "the_call_to_arms_refused"
    SHIPS_BUILT_IN_SECRET = "ships_built_in_secret"
    COMPANY_UNPAID = "the_company_left_unpaid"
    ALLY_BETRAYED = "an_ally_betrayed"
    TRIBUTE_REFUSED = "tribute_refused"
    FAITH_BROKEN_BY_CHOICE = "faith_broken_by_choice"
    BEAST_TRIBUTE_UNPAID = "tribute_to_a_beast_unpaid"
    DEMAND_UNMET = "a_demand_left_unmet"


class HouseEnd(StrEnum):
    LAST_MEMBER_DIED = "last_member_died"
    JOINED_TO_HOUSE = "joined_to_house"
    NAME_STRUCK = "name_struck"


class CoupCause(StrEnum):
    POWER_BASE = "a_subject_turned_their_power_base_on_the_throne"
    MARSHAL = "the_marshal_turned_the_army_on_the_throne"
    REGENT = "the_regent_took_the_crown"
    FACTION = "a_faction_raised_its_swords"


class DiplomacyOutcome(StrEnum):
    ALLIANCE_ACCEPTED = "alliance_accepted"
    MARRIAGE_ACCEPTED = "marriage_accepted"
    UNION_REFUSED = "union_refused"
    PEACE_MADE = "peace_made"
    PEACE_REFUSED = "peace_refused"
    TRIBUTE_SCORNED = "tribute_scorned"
    TRIBUTE_AGREED = "tribute_agreed"
