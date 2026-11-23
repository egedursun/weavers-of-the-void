from enum import StrEnum


class LandUseRing(StrEnum):
    GARDENS = "gardens"
    FORESTRY = "forestry"
    GRAIN = "grain"
    RANCHING = "ranching"
    WILDS = "wilds"


class CentralityRank(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    SEASONAL = "seasonal"
    RARE = "rare"
    METROPOLITAN = "metropolitan"


class NutrientKind(StrEnum):
    FIXED = "fixed"
    MINERAL = "mineral"
    ORGANIC = "organic"
    SALINITY = "salinity"


class PerennialKind(StrEnum):
    ORCHARD = "orchard"
    VINEYARD = "vineyard"
    GROVE = "grove"
    TIMBER = "timber"
    PLANTATION = "plantation"
    FOREST_GARDEN = "forest_garden"


class CommonsKind(StrEnum):
    PASTURE = "pasture"
    WOODS = "woods"
    FISHERY = "fishery"
    WATER = "water"
    HUNTING_GROUND = "hunting_ground"
    QUARRY = "quarry"
    SPECTRUM = "spectrum"
    ORBITS = "orbits"
    SOURCE_GROUND = "source_ground"


class CommonsRule(StrEnum):
    OPEN = "open"
    CUSTOMARY = "customary"
    COUNCIL = "council"
    ENCLOSED = "enclosed"
    STATE = "state"
    LICENSED = "licensed"


class PreparednessKind(StrEnum):
    LEVEE = "levee"
    FIREBREAK = "firebreak"
    STOCKPILE = "stockpile"
    DRILL = "drill"
    WATCHTOWER = "watchtower"
    SEAWALL = "seawall"
    QUARANTINE_PLAN = "quarantine_plan"
    SHELTERS = "shelters"
    WARNING_NETWORK = "warning_network"
    EVACUATION_ROUTES = "evacuation_routes"
    WARD = "ward"
    RESERVES_OF_ENERGY = "reserves_of_energy"


class AidKind(StrEnum):
    GOODS = "goods"
    HEALERS = "healers"
    LABOUR = "labour"
    MONEY = "money"
    CREDIT = "credit"
    FOOD = "food"
    SHELTER = "shelter"
    MEDICINE = "medicine"
    SOLDIERS = "soldiers"
    KNOWLEDGE = "knowledge"


class RebuildPlan(StrEnum):
    PLANNED = "planned"
    OPPORTUNISTIC = "opportunistic"
    RELOCATED = "relocated"
    ABANDONED = "abandoned"


class RebuildCause(StrEnum):
    FIRE = "fire"
    FLOOD = "flood"
    QUAKE = "quake"
    STORM = "storm"
    SACK = "sack"
    ERUPTION = "eruption"
    SEA_WAVE = "sea_wave"
    LANDSLIDE = "landslide"


class KeystoneUse(StrEnum):
    NAVIGATION = "navigation"
    LONGEVITY = "longevity"
    PRESCIENCE = "prescience"
    RITE = "rite"
