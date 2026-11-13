from enum import StrEnum


class AgeBand(StrEnum):
    CHILD = "child"
    ADULT = "adult"
    ELDER = "elder"


class Sex(StrEnum):
    FEMALE = "female"
    MALE = "male"


class CohortCondition(StrEnum):
    NONE = "none"
    VETERAN = "veteran"
    SICK = "sick"
    ENSLAVED = "enslaved"
    CAPTIVE = "captive"
    MAIMED = "maimed"


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


class Aesthetic(StrEnum):
    AUSTERE = "austere"
    ORNATE = "ornate"
    GEOMETRIC = "geometric"
    NATURAL = "natural"
    MACABRE = "macabre"
    CELESTIAL = "celestial"


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


class MarriageCustom(StrEnum):
    MONOGAMY = "monogamy"
    POLYGYNY = "polygyny"
    POLYANDRY = "polyandry"
    GROUP = "group"


class InheritanceCustom(StrEnum):
    GAVELKIND = "gavelkind"
    PRIMOGENITURE = "primogeniture"
    ULTIMOGENITURE = "ultimogeniture"
    MATRILINEAL = "matrilineal"
    ELECTIVE = "elective"
    BY_MERIT = "by_merit"


class FolkDiet(StrEnum):
    OMNIVORE = "omnivore"
    HERBIVORE = "herbivore"
    CARNIVORE = "carnivore"
    PISCIVORE = "piscivore"
    SCAVENGER = "scavenger"
    SANGUIVORE = "sanguivore"
    LITHOVORE = "lithovore"
    ESSENCE_FEEDER = "essence_feeder"
    PHOTOTROPH = "phototroph"


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
