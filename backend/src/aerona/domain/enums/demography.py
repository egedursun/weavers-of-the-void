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
    BERSERKER = "berserker"
    NAVAL_RAIDER = "naval_raider"
    SIEGE_ENGINEER = "siege_engineer"
    WAR_MAGIC = "war_magic"
    BEAST_WAR = "beast_war"


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
