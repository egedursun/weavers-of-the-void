from enum import StrEnum


class LawTarget(StrEnum):
    STAT = "stat"
    LIFE = "life"
    DEATH = "death"
    MAGIC = "magic"
    WAR = "war"
    HARVEST = "harvest"
    TRAVEL = "travel"
    LANGUAGE = "language"
    DISASTER = "disaster"
    MATERIAL = "material"
    LIGHT = "light"
    WEIGHT = "weight"
    SEASON = "season"
    DREAMS = "dreams"
    OATHS = "oaths"
    MADE_MINDS = "made_minds"
    COPIES = "copies"
    POWERS = "powers"
    SOURCES = "sources"
    CONCEALMENT = "concealment"
    LIVING_CRAFT = "living_craft"
    REALMS = "realms"


class LawOperator(StrEnum):
    FORBID = "forbid"
    REQUIRE = "require"
    MULTIPLY = "multiply"
    SET = "set"
    INVERT = "invert"
    BIND_TO_CONDITION = "bind_to_condition"


class LawCondition(StrEnum):
    ALWAYS = "always"
    AT_WAR = "at_war"
    AT_PEACE = "at_peace"
    COLD_SEASON = "cold_season"
    DOOM_RISING = "doom_rising"
    AUTHOR_WORSHIPPED = "author_worshipped"
    AUTHOR_FORGOTTEN = "author_forgotten"


class LawExceptionKind(StrEnum):
    PERSON = "person"
    LINE = "line"
    PEOPLE = "people"
    KIND = "kind"
    PLACE = "place"
