from enum import StrEnum
from types import MappingProxyType

from aerona.domain.enums.entity import EngineKind


class FactionKind(StrEnum):
    MERCHANT_GUILD = "merchant_guild"
    CRAFT_GUILD = "craft_guild"
    PRIESTHOOD = "priesthood"
    WARRIOR_ORDER = "warrior_order"
    NOBLE_COUNCIL = "noble_council"
    PEASANT_LEAGUE = "peasant_league"
    REBELS = "rebels"
    BANDITS = "bandits"
    PIRATES = "pirates"
    ASSASSINS = "assassins"
    SCHOLARS_ACADEMY = "scholars_academy"
    SECRET_SOCIETY = "secret_society"
    MERCENARY_COMPANY = "mercenary_company"
    INTERWORLD_FEDERATION = "interworld_federation"
    WANDERING_MARKET = "wandering_market"
    ROUTE_RAIDERS = "route_raiders"
    SOCIAL_CIRCLE = "social_circle"
    MAGE_ORDER = "mage_order"
    ESTATE = "estate"
    PARTY = "party"
    MOVEMENT = "movement"
    CHARTERED_COMPANY = "chartered_company"
    HOLY_ORDER = "holy_order"
    CRIME_FAMILY = "crime_family"
    THIEVES_GUILD = "thieves_guild"
    SMUGGLING_RING = "smuggling_ring"
    PIRATE_CONFEDERACY = "pirate_confederacy"
    ART_MOVEMENT = "art_movement"
    CLUB = "club"
    LEAGUE = "league"
    WORKERS_UNION = "workers_union"
    ENGINEERS_SOCIETY = "engineers_society"
    FINANCIERS = "financiers"
    VETERANS = "veterans"
    WORKER_BODY = "worker_body"
    STREET_GANG = "street_gang"
    TRAFFICKING_RING = "trafficking_ring"


class FactionScale(StrEnum):
    BAND = "band"
    COMPANY = "company"
    ORGANISATION = "organisation"
    NETWORK = "network"


class FactionGoalKind(StrEnum):
    LOWER_TAXES = "lower_taxes"
    MONOPOLY_ON = "monopoly_on"
    INSTALL_CLAIMANT = "install_claimant"
    ABOLISH_LAW = "abolish_law"
    ENACT_LAW = "enact_law"
    WAR_ON = "war_on"
    PEACE_WITH = "peace_with"
    PROTECT_CRAFT = "protect_craft"
    CONVERT_REALM = "convert_realm"
    INDEPENDENCE = "independence"
    LOOT = "loot"
    GAIN_PRIVILEGE = "gain_privilege"
    WIN_OFFICE = "win_office"
    RUIN_RIVAL = "ruin_rival"


class FactionActionKind(StrEnum):
    LOBBY = "lobby"
    BRIBE = "bribe"
    PETITION = "petition"
    STRIKE = "strike"
    RIOT = "riot"
    COUP = "coup"
    ASSASSINATE = "assassinate"
    SMUGGLE = "smuggle"
    RAID = "raid"
    FUND_WAR = "fund_war"
    RECRUIT = "recruit"
    SCHISM = "schism"
    SUPPRESSED = "suppressed"
    HIRED = "hired"
    DEFECTED = "defected"
    PROPAGANDA = "propaganda"
    BOYCOTT = "boycott"


class FactionRank(StrEnum):
    LEADER = "leader"
    OFFICER = "officer"
    MEMBER = "member"
    NOVICE = "novice"


class EstatePrivilege(StrEnum):
    TAX_EXEMPTION = "tax_exemption"
    MONOPOLY = "monopoly"
    COUNCIL_SEAT = "council_seat"
    ARMS = "arms"
    JUDICIAL_IMMUNITY = "judicial_immunity"
    RESERVED_OFFICES = "reserved_offices"
    LAND_HOLDING = "land_holding"


class MovementCause(StrEnum):
    ABOLITION = "abolition"
    INDEPENDENCE = "independence"
    REVIVAL = "revival"
    LAND_REFORM = "land_reform"
    FRANCHISE = "franchise"
    PEACE = "peace"
    CONSERVATION = "conservation"
    LABOUR = "labour"
    FAITH_REFORM = "faith_reform"
    TEMPERANCE = "temperance"
    MIND_RIGHTS = "mind_rights"
    EQUAL_STANDING = "equal_standing"


KIND_OF_ENGINE = MappingProxyType(
    {
        EngineKind.MERCHANT_GUILD: FactionKind.MERCHANT_GUILD,
        EngineKind.PRIESTS_COUNCIL: FactionKind.PRIESTHOOD,
        EngineKind.WARRIOR_BAND: FactionKind.WARRIOR_ORDER,
        EngineKind.REBELS: FactionKind.REBELS,
        EngineKind.ROUTE_RAIDERS: FactionKind.ROUTE_RAIDERS,
        EngineKind.INTERWORLD_FEDERATION: FactionKind.INTERWORLD_FEDERATION,
        EngineKind.WANDERING_MARKET: FactionKind.WANDERING_MARKET,
        EngineKind.MERCENARY_ARMY: FactionKind.MERCENARY_COMPANY,
        EngineKind.HOLY_GUARD: FactionKind.WARRIOR_ORDER,
        EngineKind.PEOPLES_ARMY: FactionKind.REBELS,
    }
)
