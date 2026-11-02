LOCATION_CHAIN_MAX_HOPS = 10
UNKNOWN_DISTANCE = 99
ENGINE_SEED_SEPARATOR = ":"
MANUAL_STREAM_PREFIX = "manual"
FOLDED_TEMPLATE_SUFFIX = ".folded"
PERSON_NAME_ATTEMPTS = 4
WORLD_LANGUAGE_FALLBACKS = 3
ADJACENT_HOPS = 1
DEFAULT_PROFILE_VOWELS = ("a", "e", "i", "o", "u")
DEFAULT_PROFILE_CONSONANTS = ("b", "d", "g", "k", "l", "m", "n", "r", "s", "t", "v", "z")
DEFAULT_PROFILE_SYLLABLES = ("CV", "CVC", "V")
DEFAULT_PROFILE_MIN_SYLLABLES = 1
DEFAULT_PROFILE_MAX_SYLLABLES = 3
MIN_AGING_MULTIPLIER = 0.1
ROUND_HALF = 0.5
ORDINAL_TEEN_CYCLE = 100
ORDINAL_DIGIT_CYCLE = 10
ORDINAL_TEEN_FIRST = 11
ORDINAL_TEEN_LAST = 13
ORDINAL_DEFAULT_SUFFIX = "th"
ORDINAL_SUFFIXES = {1: "st", 2: "nd", 3: "rd"}
SUBTREE_STEP_LIMIT = 5000
UNBOUNDED_STAT = 10**12
SURVIVAL_STORY_CHANCE = 50
UNRUNNABLE_PHASES = frozenset({"advance_epoch"})
HEAVY_PHASES = frozenset(
    {
        "campaigns",
        "monster_raids",
        "disasters",
        "dark_ages",
        "creatures",
        "migration",
        "civilization",
        "population_growth",
        "population_baseline",
        "sons_renewal",
        "gods_fate",
        "doom_clock",
        "creator_essence",
        "epoch_statistics",
        "mortal_aging",
        "mortal_wounds",
        "ruins",
    }
)
FNV_OFFSET = 2166136261
FNV_PRIME = 16777619
U32_MASK = 0xFFFFFFFF
U32_SPAN = 4294967296
