from enum import StrEnum


class AgeBand(StrEnum):
    INFANT = "infant"
    CHILD = "child"
    YOUTH = "youth"
    ADULT = "adult"
    ELDER = "elder"
    ANCIENT = "ancient"


class SexKind(StrEnum):
    BEARER = "bearer"
    BEGETTER = "begetter"
    BOTH = "both"
    NEITHER = "neither"
    NONE = "none"


class CohortCondition(StrEnum):
    NONE = "none"
    VETERAN = "veteran"
    SICK = "sick"
    ENSLAVED = "enslaved"
    CAPTIVE = "captive"
    MAIMED = "maimed"
    ORPHANED = "orphaned"
    DISPLACED = "displaced"
    INDEBTED = "indebted"
    GIFTED = "gifted"


class Job(StrEnum):
    FARMING = "farming"
    HERDING = "herding"
    FISHING = "fishing"
    MINING = "mining"
    CRAFTING = "crafting"
    TRADE = "trade"
    SOLDIERING = "soldiering"
    CLERGY = "clergy"
    SCHOLARSHIP = "scholarship"
    BUILDING = "building"
    SERVICE = "service"
    IDLE = "idle"
    TRANSPORT = "transport"
    ADMINISTRATION = "administration"
    GATHERING = "gathering"
    INDUSTRY = "industry"
    ARTS = "arts"
    HEALING = "healing"
    TEACHING = "teaching"


class MotifSource(StrEnum):
    LIVING_THINGS = "living_things"
    LAND = "land"
    SKY = "sky"
    GODS = "gods"
    ANCESTORS = "ancestors"
    PEOPLE = "people"
    MADE_THINGS = "made_things"
    WRITING = "writing"
    PATTERN = "pattern"


class MartialStyle(StrEnum):
    SHIELDWALL = "shieldwall"
    HORSE_ARCHER = "horse_archer"
    SKIRMISHER = "skirmisher"
    CHARIOT = "chariot"
    PHALANX = "phalanx"
    SHOCK = "shock"
    NAVAL_RAIDER = "naval_raider"
    SIEGE_ENGINEER = "siege_engineer"
    WAR_MAGIC = "war_magic"
    BEAST_WAR = "beast_war"
    MECHANISED = "mechanised"
    AIR_MOBILE = "air_mobile"
    GUERRILLA = "guerrilla"
    DRONE_WAR = "drone_war"
    ORBITAL = "orbital"
    COMBINED_ARMS = "combined_arms"


class InheritanceCustom(StrEnum):
    EQUAL_SHARES = "equal_shares"
    PRIMOGENITURE = "primogeniture"
    ULTIMOGENITURE = "ultimogeniture"
    THROUGH_SECOND_LINE = "through_second_line"
    ELECTIVE = "elective"
    BY_MERIT = "by_merit"
    SENIORITY = "seniority"
    DESIGNATED = "designated"
    COMMUNAL = "communal"


class NaturalTrait(StrEnum):
    DARK_SIGHT = "dark_sight"
    COLD_BLOODED = "cold_blooded"
    WINGED = "winged"
    AMPHIBIOUS = "amphibious"
    THICK_HIDE = "thick_hide"
    KEEN_SENSES = "keen_senses"
    VENOMOUS = "venomous"
    REGENERATING = "regenerating"
    BURROWING = "burrowing"
    HIVE_MINDED = "hive_minded"


class FuneralCustom(StrEnum):
    BURIAL = "burial"
    CREMATION = "cremation"
    SKY_BURIAL = "sky_burial"
    SEA_BURIAL = "sea_burial"
    ENTOMBMENT = "entombment"
    ANCESTOR_SHRINE = "ancestor_shrine"
    ENDOCANNIBALISM = "endocannibalism"
    REANIMATION = "reanimation"
    SOUL_BINDING = "soul_binding"
    NAMELESS = "nameless"
    NONE = "none"
    MUMMIFICATION = "mummification"
    SECONDARY_BURIAL = "secondary_burial"
    RETURN_TO_SOIL = "return_to_soil"
    MEMORIAL_ONLY = "memorial_only"
