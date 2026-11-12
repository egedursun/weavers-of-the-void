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
    RARE = "rare"


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


class CommonsKind(StrEnum):
    PASTURE = "pasture"
    WOODS = "woods"
    FISHERY = "fishery"


class CommonsRule(StrEnum):
    OPEN = "open"
    CUSTOMARY = "customary"
    COUNCIL = "council"
    ENCLOSED = "enclosed"


class PreparednessKind(StrEnum):
    LEVEE = "levee"
    FIREBREAK = "firebreak"
    STOCKPILE = "stockpile"
    DRILL = "drill"
    WATCHTOWER = "watchtower"
    SEAWALL = "seawall"


class AidKind(StrEnum):
    GOODS = "goods"
    HEALERS = "healers"
    LABOUR = "labour"


class RebuildPlan(StrEnum):
    PLANNED = "planned"
    OPPORTUNISTIC = "opportunistic"


class RebuildCause(StrEnum):
    FIRE = "fire"
    FLOOD = "flood"
    QUAKE = "quake"
    STORM = "storm"
    SACK = "sack"


class KeystoneUse(StrEnum):
    NAVIGATION = "navigation"
    LONGEVITY = "longevity"
    PRESCIENCE = "prescience"
    RITE = "rite"
