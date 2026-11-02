from enum import StrEnum


class WorldType(StrEnum):
    ORDINARY = "ordinary"
    OCEAN = "ocean"
    SAND = "sand"
    ICE = "ice"
    LAVA = "lava"
    CRYSTAL = "crystal"
    LIVING = "living"
    DEAD = "dead"
    DREAM = "dream"
    MIRROR = "mirror"
    GAS = "gas"
    RINGED = "ringed"
    ASTEROID_BELT = "asteroid_belt"
    TIDALLY_LOCKED = "tidally_locked"
    VOID_POCKET = "void_pocket"
    GODS_PALACE = "gods_palace"
    GENERATION_SHIP = "generation_ship"
    CORPSE_WORLD = "corpse_world"


class Gravity(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class Atmosphere(StrEnum):
    NONE = "none"
    THIN = "thin"
    NORMAL = "normal"
    DENSE = "dense"
    TOXIC = "toxic"


class Discovery(StrEnum):
    KNOWN = "known"
    LEGEND = "legend"
    UNKNOWN = "unknown"
    FORGOTTEN = "forgotten"


class StarType(StrEnum):
    YELLOW_DWARF = "yellow_dwarf"
    RED_GIANT = "red_giant"
    BLUE_GIANT = "blue_giant"
    BINARY = "binary"
    WHITE_DWARF = "white_dwarf"
    DEAD_STAR = "dead_star"
    BLACK_SUN = "black_sun"
    BROKEN_STAR = "broken_star"
    PULSAR = "pulsar"
    STAR_REMNANT = "star_remnant"
    REBORN_STAR = "reborn_star"


DARK_STAR_TYPES = frozenset({StarType.DEAD_STAR, StarType.BLACK_SUN, StarType.BROKEN_STAR, StarType.STAR_REMNANT})
COLLAPSIBLE_STAR_TYPES = frozenset({StarType.RED_GIANT, StarType.BLUE_GIANT, StarType.BROKEN_STAR, StarType.PULSAR})


class ClimateEra(StrEnum):
    TEMPERATE = "temperate"
    DROUGHT = "drought"
    RAIN = "rain"
    ICE_AGE = "ice_age"
    SCORCHING = "scorching"


class SkyEventKind(StrEnum):
    ECLIPSE = "eclipse"
    COMET = "comet"
    ALIGNMENT = "alignment"
    SUPERNOVA = "supernova"
    BLACK_SUN = "black_sun"
    VOID_STORM = "void_storm"


class HorrorEventKind(StrEnum):
    STARS_ALIGN = "stars_align"
    EYE_IN_THE_SKY = "eye_in_the_sky"
    WAVE_OF_SILENCE = "wave_of_silence"
    REVERSE_RAIN = "reverse_rain"
    VISIT_OF_THE_VOID = "visit_of_the_void"


class LoreLanguage(StrEnum):
    ENGLISH = "english"
    TURKISH = "turkish"


class FateMode(StrEnum):
    AUTO = "auto"
    OFF = "off"


class SonDistribution(StrEnum):
    AUTO = "auto"
    MANUAL = "manual"


class CosmosSize(StrEnum):
    SINGLE = "single"
    SMALL = "small"
    LARGE = "large"


class TechnologyEra(StrEnum):
    STONE = "stone"
    BRONZE = "bronze"
    IRON = "iron"
    MEDIEVAL = "medieval"
    RENAISSANCE = "renaissance"
    STEAM = "steam"


class LanguageTexture(StrEnum):
    FLOWING = "flowing"
    HARD = "hard"
    GUTTURAL = "guttural"
    SIBILANT = "sibilant"
    LONG = "long"
    FREE = "free"


class GenesisTemplate(StrEnum):
    DARK_FANTASY = "dark_fantasy"
    MYTHIC_AGE = "mythic_age"
    COSMIC_HORROR = "cosmic_horror"
    FAIRY_TALE = "fairy_tale"
    STAR_MYTH = "star_myth"
    SAND_AND_ASH = "sand_and_ash"
    PRIMORDIAL_DAWN = "primordial_dawn"
    CROWNS_AND_KNIVES = "crowns_and_knives"
    DROWNED_WORLD = "drowned_world"
    LONG_WINTER = "long_winter"
    AFTER_THE_FALL = "after_the_fall"
    SKY_ISLANDS = "sky_islands"
    AGE_OF_ENGINES = "age_of_engines"
