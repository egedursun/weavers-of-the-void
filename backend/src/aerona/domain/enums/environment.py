from enum import StrEnum


class TerrainKind(StrEnum):
    PLAIN = "plain"
    STEPPE = "steppe"
    FOREST = "forest"
    JUNGLE = "jungle"
    MARSH = "marsh"
    HILLS = "hills"
    MOUNTAINS = "mountains"
    HIGH_PASS = "high_pass"
    DESERT = "desert"
    TUNDRA = "tundra"
    ICE_SHEET = "ice_sheet"
    VOLCANIC = "volcanic"
    COAST = "coast"
    ISLAND = "island"
    RIVER_VALLEY = "river_valley"
    CANYON = "canyon"
    UNDERGROUND = "underground"
    CRYSTAL_FIELD = "crystal_field"
    FLESH = "flesh"
    VOID_SHORE = "void_shore"
    RUIN_FIELD = "ruin_field"
    URBAN = "urban"
    SEA = "sea"
    TAIGA = "taiga"
    SAVANNA = "savanna"
    MANGROVE = "mangrove"
    EVAPORITE_FLAT = "evaporite_flat"
    KARST = "karst"
    REGOLITH_PLAIN = "regolith_plain"
    CLOUD_DECK = "cloud_deck"
    BADLANDS = "badlands"
    MOOR = "moor"
    SCRUBLAND = "scrubland"
    FLOODPLAIN = "floodplain"


class SoilKind(StrEnum):
    THIN = "thin"
    LOAM = "loam"
    CLAY = "clay"
    SAND = "sand"
    VOLCANIC = "volcanic"
    PEAT = "peat"
    SALINE = "saline"
    TEPHRA = "tephra"
    CRYSTALLINE = "crystalline"
    CALCAREOUS = "calcareous"
    LATERITE = "laterite"
    PERMAFROST = "permafrost"
    REGOLITH = "regolith"
    ARTIFICIAL = "artificial"
    HUMIC = "humic"
    LEACHED = "leached"
    SILT = "silt"
    GLEY = "gley"
    CRACKING_CLAY = "cracking_clay"


class TemperatureBand(StrEnum):
    FROZEN = "frozen"
    COLD = "cold"
    TEMPERATE = "temperate"
    WARM = "warm"
    HOT = "hot"
    SEARING = "searing"


class RiverClass(StrEnum):
    NONE = "none"
    STREAM = "stream"
    RIVER = "river"
    GREAT_RIVER = "great_river"


class CoastKind(StrEnum):
    NONE = "none"
    CLIFF = "cliff"
    BEACH = "beach"
    HARBOUR_SITE = "harbour_site"
    REEF = "reef"


class ScarKind(StrEnum):
    BATTLEFIELD = "battlefield"
    PLAGUE_GROUND = "plague_ground"
    MADE_BARREN = "made_barren"
    BURNED = "burned"
    CRATER = "crater"
    HAUNTED = "haunted"
    BLIGHTED = "blighted"
    LEAK_WOUND = "leak_wound"
    PLUNDERED = "plundered"
    EARTHWORKS = "earthworks"
    MILITARY_ROAD = "military_road"
    BRIDGE_DOWN = "bridge_down"
    FLOODED = "flooded"
    POISONED = "poisoned"
    MINED_OUT = "mined_out"
    ERODED = "eroded"
    DEFORESTED = "deforested"
    DRAINED = "drained"
    OVERGRAZED = "overgrazed"


class CleansingMethod(StrEnum):
    WORKS = "works"
    RITE = "rite"
    POWER = "power"


class MovementMode(StrEnum):
    ON_FOOT = "on_foot"
    MOUNTED = "mounted"
    WHEELED = "wheeled"
    BOAT = "boat"
    FLYING = "flying"
    BURROWING = "burrowing"
    SUBMERGED = "submerged"
    INCORPOREAL = "incorporeal"
    SWIMMING = "swimming"
    CLIMBING = "climbing"


class WorldLink(StrEnum):
    WORLD = "world"
    ENTITY = "entity"
    INCIDENT = "incident"


class SeasonDating(StrEnum):
    POSITION = "position"
    DAY = "day"


class SeasonWarmth(StrEnum):
    COLDEST = "coldest"
    COLD = "cold"
    COOLING = "cooling"
    EVEN = "even"
    WARMING = "warming"
    WARM = "warm"
    WARMEST = "warmest"


class SeasonWater(StrEnum):
    ARID = "arid"
    DRY = "dry"
    EVEN = "even"
    WET = "wet"
    DELUGE = "deluge"


class SeasonOnset(StrEnum):
    EARLY = "early"
    ON_TIME = "on_time"
    LATE = "late"
    FAILED = "failed"


class MovementMedium(StrEnum):
    GROUND = "ground"
    WATER_SURFACE = "water_surface"
    UNDER_WATER = "under_water"
    AIR = "air"
    THROUGH_MATTER = "through_matter"


class MovementWork(StrEnum):
    ROADS = "roads"
    BRIDGES = "bridges"
    HARBOURS = "harbours"


class LandUse(StrEnum):
    CLEARED = "cleared"
    FARMED = "farmed"
    GRAZED = "grazed"
    MINED = "mined"
    BUILT = "built"


class WeatherKind(StrEnum):
    CLEAR = "clear"
    OVERCAST = "overcast"
    RAIN = "rain"
    DOWNPOUR = "downpour"
    STORM = "storm"
    FOG = "fog"
    SNOW = "snow"
    BLIZZARD = "blizzard"
    HEAT_WAVE = "heat_wave"
    DROUGHT_WIND = "drought_wind"
    SANDSTORM = "sandstorm"
    HAIL = "hail"
    MAGIC_STORM = "magic_storm"
    ASH_FALL = "ash_fall"
    VOID_RAIN = "void_rain"
    ECLIPSE_DARK = "eclipse_dark"
    AURORA = "aurora"
    FROST = "frost"
    ICE_STORM = "ice_storm"
    DRIZZLE = "drizzle"
    SLEET = "sleet"
    FREEZING_FOG = "freezing_fog"
    THUNDERSTORM = "thunderstorm"
    TORNADO = "tornado"
    CYCLONE = "cyclone"


class TerrainTrait(StrEnum):
    WOODED = "wooded"
    OPEN = "open"
    ROUGH = "rough"
    HIGH = "high"
    WET = "wet"
    ARID = "arid"
    COLD = "cold"
    HOT = "hot"
    COASTAL = "coastal"
    WATERY = "watery"
    UNDERGROUND = "underground"
    BUILT = "built"
    AMBUSH_COVER = "ambush_cover"
    CONFINED = "confined"
    SLIPPERY = "slippery"
    NON_MINERAL_GROUND = "non_mineral_ground"
    AIRLESS = "airless"
    GASEOUS = "gaseous"
    FERTILE = "fertile"


class WeatherDraw(StrEnum):
    COLD = "cold"
    HOT = "hot"
    DRY = "dry"
    DRY_HOT = "dry_hot"
    WET = "wet"
    WET_LIQUID = "wet_liquid"
    CLEAR = "clear"
    EVEN = "even"
    AURORA = "aurora"
    MAGIC = "magic"
    ASH = "ash"
    VOID = "void"
    ECLIPSE = "eclipse"
    FREEZING_CLEAR = "freezing_clear"
    FREEZING_WET = "freezing_wet"
    WET_HOT = "wet_hot"
    WARM_SEA = "warm_sea"


class WeatherTrait(StrEnum):
    COLD = "cold"
    SNOW_COVER = "snow_cover"
    WET = "wet"
    LIQUID = "liquid"
    HOT = "hot"
    DRY = "dry"
    WINDY = "windy"
    STORM = "storm"
    COVERING = "covering"
    SLOWING = "slowing"
    HEAVY = "heavy"
    EXTREME = "extreme"
    ICY = "icy"


class WeatherEffect(StrEnum):
    VISIBILITY = "visibility"
    FOOTING = "footing"
    COLD = "cold"
    HEAT = "heat"
    WET = "wet"
    WIND = "wind"
    MORALE = "morale"
    GROWTH = "growth"
    LIGHTNING = "lightning"
    FLOOD = "flood"
    BREATH = "breath"


class NotableYearKind(StrEnum):
    HUNGER = "hunger"
    PLENTY = "plenty"
    WEATHER = "weather"
    PESTILENCE = "pestilence"
    DISASTER = "disaster"
    DISCOVERY = "discovery"
    CONTACT = "contact"
    OMEN = "omen"
    PEACE = "peace"
    FOUNDING = "founding"


class PlaceCover(StrEnum):
    OPEN = "open"
    LIGHT = "light"
    HEAVY = "heavy"


class WaterSource(StrEnum):
    NONE = "none"
    SPRING = "spring"
    WELL = "well"
    RIVER = "river"
    LAKE = "lake"
    SEA = "sea"


class ClimateTurn(StrEnum):
    WARMER = "warmer"
    COLDER = "colder"
    WETTER = "wetter"
    DRIER = "drier"
