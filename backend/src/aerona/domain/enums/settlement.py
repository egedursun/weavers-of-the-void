from enum import StrEnum


class SizeTier(StrEnum):
    HAMLET = "hamlet"
    VILLAGE = "village"
    TOWN = "town"
    CITY = "city"
    METROPOLIS = "metropolis"


TIER_ORDER = (SizeTier.HAMLET, SizeTier.VILLAGE, SizeTier.TOWN, SizeTier.CITY, SizeTier.METROPOLIS)


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
