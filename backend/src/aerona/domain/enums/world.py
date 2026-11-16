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
    SUPER_EARTH = "super_earth"
    ICE_GIANT = "ice_giant"
    HOT_GIANT = "hot_giant"
    IRON = "iron"
    CARBON = "carbon"
    GREENHOUSE = "greenhouse"
    DWARF_PLANET = "dwarf_planet"
    CHTHONIAN = "chthonian"
    HYCEAN = "hycean"
    JUNGLE = "jungle"
    FORGE = "forge"
    FUNGAL = "fungal"
    SHATTERED = "shattered"
    HOLLOW = "hollow"
    ICE_SHELL = "ice_shell"
    METHANE = "methane"


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
    BLUE_STAR = "blue_star"
    BLUE_WHITE_STAR = "blue_white_star"
    WHITE_STAR = "white_star"
    YELLOW_WHITE_STAR = "yellow_white_star"
    ORANGE_DWARF = "orange_dwarf"
    RED_DWARF = "red_dwarf"
    BROWN_DWARF = "brown_dwarf"
    YELLOW_GIANT = "yellow_giant"
    RED_SUPERGIANT = "red_supergiant"
    BLUE_SUPERGIANT = "blue_supergiant"
    HYPERGIANT = "hypergiant"
    WOLF_RAYET = "wolf_rayet"
    PROTOSTAR = "protostar"
    CARBON_STAR = "carbon_star"
    NEUTRON_STAR = "neutron_star"
    MAGNETAR = "magnetar"
    BLACK_HOLE = "black_hole"
    VARIABLE_STAR = "variable_star"
    TRINARY = "trinary"
    CHAINED_STAR = "chained_star"
    WATCHING_STAR = "watching_star"


DARK_STAR_TYPES = frozenset({StarType.DEAD_STAR, StarType.BLACK_SUN, StarType.BROKEN_STAR, StarType.STAR_REMNANT, StarType.BLACK_HOLE})
EXTINGUISHED_STAR_TYPES = frozenset({StarType.DEAD_STAR, StarType.BLACK_SUN, StarType.STAR_REMNANT, StarType.BLACK_HOLE})


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
    FLARE = "flare"
    AURORA = "aurora"
    TRANSIT = "transit"


class HorrorEventKind(StrEnum):
    STARS_ALIGN = "stars_align"
    EYE_IN_THE_SKY = "eye_in_the_sky"
    WAVE_OF_SILENCE = "wave_of_silence"
    REVERSE_RAIN = "reverse_rain"
    VISIT_OF_THE_VOID = "visit_of_the_void"
    THE_DIMMING = "the_dimming"
    WHISPERS_FROM_BEYOND = "whispers_from_beyond"


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


class CosmosShape(StrEnum):
    ONE_SUN = "one_sun"
    MANY_SUNS = "many_suns"
    LAYERED = "layered"


class TechnologyEra(StrEnum):
    STONE = "stone"
    BRONZE = "bronze"
    IRON = "iron"
    MEDIEVAL = "medieval"
    RENAISSANCE = "renaissance"
    STEAM = "steam"
    ELECTRICAL = "electrical"
    INFORMATION = "information"
    ADVANCED = "advanced"


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
    MANY_SUNS = "many_suns"
    LAYERED_REALMS = "layered_realms"
    LIVING_WORLD = "living_world"
    DREAMING_WORLD = "dreaming_world"
    GENERATION_SHIP = "generation_ship"
    WITHOUT_MAGIC = "without_magic"
    ELECTRIC_AGE = "electric_age"
    INFORMATION_AGE = "information_age"
    ADVANCED_AGE = "advanced_age"
    MADE_MINDS = "made_minds"
    AFTER_ABUNDANCE = "after_abundance"


class ImageStyle(StrEnum):
    PHOTOREAL = "photoreal"
    PAINTING = "painting"
    INK = "ink"
    WATERCOLOR = "watercolor"
    ANIME = "anime"
    CUSTOM = "custom"
