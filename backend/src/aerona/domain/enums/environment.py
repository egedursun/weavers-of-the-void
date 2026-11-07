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


class SoilKind(StrEnum):
    THIN = "thin"
    LOAM = "loam"
    CLAY = "clay"
    SAND = "sand"
    VOLCANIC = "volcanic"
    PEAT = "peat"
    SALT = "salt"
    ASH = "ash"
    CRYSTAL = "crystal"
    BONE = "bone"


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
    SALTED_EARTH = "salted_earth"
    BURNED = "burned"
    CRATER = "crater"
    HAUNTED = "haunted"
    BLIGHTED = "blighted"
    LEAK_WOUND = "leak_wound"
    PLUNDERED = "plundered"
    EARTHWORKS = "earthworks"
    MILITARY_ROAD = "military_road"
    BRIDGE_DOWN = "bridge_down"


class MovementMode(StrEnum):
    ON_FOOT = "on_foot"
    MOUNTED = "mounted"
    WHEELED = "wheeled"
    BOAT = "boat"
    FLYING = "flying"
    BURROWING = "burrowing"


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


class WeatherEffect(StrEnum):
    VISIBILITY = "visibility"
    FOOTING = "footing"
    COLD = "cold"
    HEAT = "heat"
    WET = "wet"
    WIND = "wind"
    MORALE = "morale"
    GROWTH = "growth"


class NotableYearKind(StrEnum):
    HUNGER = "hunger"
    PLENTY = "plenty"
    WEATHER = "weather"
    PESTILENCE = "pestilence"


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
