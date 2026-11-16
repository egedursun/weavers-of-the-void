from enum import StrEnum


class SizeTier(StrEnum):
    HAMLET = "hamlet"
    VILLAGE = "village"
    TOWN = "town"
    CITY = "city"
    METROPOLIS = "metropolis"
    MEGALOPOLIS = "megalopolis"
    WORLD_CITY = "world_city"


TIER_ORDER = (SizeTier.HAMLET, SizeTier.VILLAGE, SizeTier.TOWN, SizeTier.CITY, SizeTier.METROPOLIS, SizeTier.MEGALOPOLIS, SizeTier.WORLD_CITY)


class DistrictKind(StrEnum):
    FARMLAND = "farmland"
    MARKET = "market"
    CRAFT_QUARTER = "craft_quarter"
    TEMPLE_QUARTER = "temple_quarter"
    HARBOUR = "harbour"
    CITADEL = "citadel"
    SLUMS = "slums"
    PALACE = "palace"
    FOREIGN_QUARTER = "foreign_quarter"
    NECROPOLIS = "necropolis"
    RESIDENTIAL = "residential"
    CIVIC_QUARTER = "civic_quarter"
    GARDENS = "gardens"
    INDUSTRIAL = "industrial"
    BUSINESS = "business"
    RESEARCH = "research"
    TRANSPORT_HUB = "transport_hub"
    MILITARY_BASE = "military_base"
    UNIVERSITY = "university"
    ENTERTAINMENT = "entertainment"
    SUBURB = "suburb"
    ARCOLOGY = "arcology"


class DistrictHarm(StrEnum):
    FLOOD = "flood"
    EARTHQUAKE = "earthquake"
    STORM = "storm"
    DROUGHT = "drought"
    SACK = "sack"


class BuildMaterial(StrEnum):
    TIMBER = "timber"
    STONE = "stone"


class WaterSupply(StrEnum):
    NONE = "none"
    WELL = "well"
    CISTERN = "cistern"
    AQUEDUCT = "aqueduct"


WATER_ORDER = (WaterSupply.NONE, WaterSupply.WELL, WaterSupply.CISTERN, WaterSupply.AQUEDUCT)


class TreasuryEntry(StrEnum):
    TAX = "tax"
    TOLLS = "tolls"
    INVESTMENT = "investment"
    GARRISON = "garrison"
    WALLS = "walls"
    BUILDING = "building"
    FESTIVAL = "festival"
    ALMS = "alms"
    FIRE = "fire"
    PLUNDER = "plunder"
    GRANT = "grant"
    LOAN = "loan"
    UPKEEP = "upkeep"
    OFFICE_SALE = "office_sale"
    RELIEF = "relief"
    REBUILDING = "rebuilding"
    MONOPOLY = "monopoly"
