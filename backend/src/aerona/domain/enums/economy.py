from enum import StrEnum


class CommodityFamily(StrEnum):
    SUBSISTENCE = "subsistence"
    INDUSTRIAL = "industrial"
    STRATEGIC = "strategic"
    LUXURY = "luxury"


class CommodityKind(StrEnum):
    GRAIN = "grain"
    LIVESTOCK = "livestock"
    FISH = "fish"
    FODDER = "fodder"
    TIMBER = "timber"
    FUEL = "fuel"
    BREAD = "bread"
    ORE = "ore"
    STONE = "stone"
    CLOTH = "cloth"
    TOOLS = "tools"
    WEAPONS = "weapons"
    ARMOUR = "armour"
    MOUNTS = "mounts"
    SIEGE_MATERIEL = "siege_materiel"
    MEDICINE = "medicine"
    LUXURIES = "luxuries"
    INCENSE = "incense"
    SACRED_GOODS = "sacred_goods"
    MAGICAL_REAGENTS = "magical_reagents"


class MaterialFamily(StrEnum):
    ORGANIC = "organic"
    STONE = "stone"
    METAL = "metal"
    PRECIOUS = "precious"
    EXOTIC = "exotic"


class MaterialOrigin(StrEnum):
    CATALOG = "catalog"
    GOD_REMAINS = "god_remains"
    DEAD_STAR = "dead_star"
    BEAST = "beast"
    LEAK_CRYSTAL = "leak_crystal"
    RESEARCH = "research"
    DIVINE = "divine"


class FoeNature(StrEnum):
    UNDEAD = "undead"
    CURSED = "cursed"
    VOID = "void"


class MaterialSlot(StrEnum):
    BODY = "body"
    WEAPONS = "weapons"
    ARMOUR = "armour"
    HULL = "hull"
    FABRIC = "fabric"


class WorkshopKind(StrEnum):
    MARKET = "market"
    GRANARY = "granary"
    WAREHOUSE = "warehouse"
    MINE = "mine"
    LUMBER_CAMP = "lumber_camp"
    FISHERY = "fishery"
    CHARCOAL_KILN = "charcoal_kiln"
    FORGE = "forge"
    TANNERY = "tannery"
    MILL = "mill"
    BREWERY = "brewery"
    WEAVERY = "weavery"
    STABLE = "stable"
    MASON_YARD = "mason_yard"
    SHIPYARD = "shipyard"
    SIEGE_YARD = "siege_yard"
    ALCHEMIST = "alchemist"
    SHRINE_WORKSHOP = "shrine_workshop"
    MINT = "mint"


class ExtractionKind(StrEnum):
    MINING = "mining"
    QUARRYING = "quarrying"
    LOGGING = "logging"
    FISHING = "fishing"
    HERDING = "herding"
    FARMING = "farming"
    GATHERING = "gathering"


class HazardKind(StrEnum):
    CAVE_IN = "cave_in"
    FLOODED_SHAFT = "flooded_shaft"
    FELLING_ACCIDENT = "felling_accident"
    DROWNING = "drowning"
    GORING = "goring"


class TradeMode(StrEnum):
    ROAD = "road"
    RIVER = "river"
    SEA = "sea"
    CARAVAN = "caravan"
    SKY = "sky"


class TradeRouteStatus(StrEnum):
    FORMING = "forming"
    OPEN = "open"
    BLOCKADED = "blockaded"
    CLOSED = "closed"
    DECAYED = "decayed"


class TradeLoss(StrEnum):
    BANDITS = "bandits"
    SEA = "sea"
    BEASTS = "beasts"
    WEATHER = "weather"


class LoanStatus(StrEnum):
    OPEN = "open"
    REPAID = "repaid"
    DEFAULTED = "defaulted"
    FORGIVEN = "forgiven"


class GoodsFlow(StrEnum):
    EXTRACTION = "extraction"
    HARVEST = "harvest"
    PRODUCTION = "production"
    INPUT = "input"
    CONSUMPTION = "consumption"
    TRADE = "trade"
    TRIBUTE = "tribute"
    AID = "aid"
    LOOT = "loot"
    LOSS = "loss"
    SIEGE = "siege"
    WAR = "war"
    CONSTRUCTION = "construction"
    OVERFLOW = "overflow"
    DECAY = "decay"
    PLAYER = "player"
    TOOL = "tool"
    SEED = "seed"
    OFFERING = "offering"


GOODS_TRANSFERS = frozenset({GoodsFlow.TRADE, GoodsFlow.TRIBUTE, GoodsFlow.AID, GoodsFlow.LOOT})
GOODS_SOURCES = frozenset({GoodsFlow.EXTRACTION, GoodsFlow.HARVEST, GoodsFlow.PRODUCTION, GoodsFlow.SEED})
GOODS_SINKS = frozenset(
    {
        GoodsFlow.INPUT,
        GoodsFlow.OFFERING,
        GoodsFlow.CONSUMPTION,
        GoodsFlow.LOSS,
        GoodsFlow.SIEGE,
        GoodsFlow.WAR,
        GoodsFlow.CONSTRUCTION,
        GoodsFlow.OVERFLOW,
        GoodsFlow.DECAY,
    }
)
