from enum import StrEnum


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


class FoundableFaction(StrEnum):
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
    CRIME_FAMILY = "crime_family"
    THIEVES_GUILD = "thieves_guild"
    SMUGGLING_RING = "smuggling_ring"
    PIRATE_CONFEDERACY = "pirate_confederacy"
    WORKERS_UNION = "workers_union"
    ENGINEERS_SOCIETY = "engineers_society"
    FINANCIERS = "financiers"
    VETERANS = "veterans"


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


class FactionRank(StrEnum):
    LEADER = "leader"
    OFFICER = "officer"
    MEMBER = "member"
    NOVICE = "novice"


CRIME_KINDS = frozenset({FactionKind.CRIME_FAMILY, FactionKind.THIEVES_GUILD, FactionKind.SMUGGLING_RING, FactionKind.PIRATE_CONFEDERACY})
OUTLAW_KINDS = frozenset({FactionKind.REBELS, FactionKind.BANDITS, FactionKind.PIRATES, FactionKind.ROUTE_RAIDERS, FactionKind.ASSASSINS, *CRIME_KINDS})
ROBBER_KINDS = frozenset({FactionKind.BANDITS, FactionKind.PIRATES, FactionKind.ROUTE_RAIDERS, FactionKind.REBELS, FactionKind.PIRATE_CONFEDERACY})
GUILD_KINDS = frozenset({FactionKind.MERCHANT_GUILD, FactionKind.CRAFT_GUILD, FactionKind.WANDERING_MARKET})
ARMED_KINDS = frozenset(
    {
        FactionKind.WARRIOR_ORDER,
        FactionKind.REBELS,
        FactionKind.BANDITS,
        FactionKind.PIRATES,
        FactionKind.ROUTE_RAIDERS,
        FactionKind.MERCENARY_COMPANY,
        FactionKind.CRIME_FAMILY,
        FactionKind.PIRATE_CONFEDERACY,
    }
)
SECRET_KINDS = frozenset({FactionKind.ASSASSINS, FactionKind.SECRET_SOCIETY, FactionKind.THIEVES_GUILD, FactionKind.SMUGGLING_RING})


class EstatePrivilege(StrEnum):
    TAX_EXEMPTION = "tax_exemption"
    MONOPOLY = "monopoly"
    COUNCIL_SEAT = "council_seat"
    ARMS = "arms"
    JUDICIAL_IMMUNITY = "judicial_immunity"


class MovementCause(StrEnum):
    ABOLITION = "abolition"
    INDEPENDENCE = "independence"
    REVIVAL = "revival"
    LAND_REFORM = "land_reform"
    FRANCHISE = "franchise"
    PEACE = "peace"
