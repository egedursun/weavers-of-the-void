from enum import StrEnum


class HorrorTarget(StrEnum):
    LIGHT = "light"
    SOUND = "sound"
    WEATHER = "weather"
    TIME = "time"
    MEMORY = "memory"
    LANGUAGE = "language"
    SLEEP = "sleep"
    BODIES = "bodies"
    MINDS = "minds"
    THE_DEAD = "the_dead"
    PLACE = "place"
    LAW = "law"


class HorrorEffect(StrEnum):
    SUPPRESS = "suppress"
    INVERT = "invert"
    DISTORT = "distort"
    MULTIPLY = "multiply"
    TAKE = "take"
    REVEAL = "reveal"
    MARK = "mark"


class HorrorScope(StrEnum):
    PERSON = "person"
    COMMUNITY = "community"
    REGION = "region"
    WORLD = "world"


class HorrorSense(StrEnum):
    SEEN = "seen"
    HEARD = "heard"
    FELT = "felt"
    DREAMED = "dreamed"
    ABSENT = "absent"
    NOT_PERCEIVED = "not_perceived"


class HorrorSource(StrEnum):
    OUTER_BEING = "outer_being"
    RIFT = "rift"
    PHENOMENON = "phenomenon"
    GOD = "god"
    MADE_THING = "made_thing"
    UNKNOWN = "unknown"
