from enum import StrEnum


class IdentityLayer(StrEnum):
    PEOPLE = "people"
    FAITH = "faith"
    CLASS = "class"
    LOCALITY = "locality"
    HOUSE = "house"
    PROFESSION = "profession"
    GENERATION = "generation"
    POLITY = "polity"
    CIRCLE = "circle"
    LANGUAGE = "language"
    KIND = "kind"
    CAUSE = "cause"


class SalienceDriver(StrEnum):
    BASELINE = "baseline"
    HOLY_WAR = "holy_war"
    FAMINE = "famine"
    INVASION = "invasion"
    STRIKE = "strike"
    RHETORIC = "rhetoric"
    SEGREGATION = "segregation"
    CROSSING = "crossing"
    GOD = "god"
    PERSECUTION = "persecution"
    COMMEMORATION = "commemoration"
    ELECTION = "election"
    CONTEST = "contest"


class PlayKind(StrEnum):
    GAMES = "games"
    MOCK_FIGHTS = "mock_fights"
    IMITATION = "imitation"
    RIDING = "riding"
    ARCHERY = "archery"
    SONGS = "songs"


class SanctuaryKind(StrEnum):
    TEMPLE = "temple"
    HOSPITALITY = "hospitality"
    ASYLUM = "asylum"
    WILDS = "wilds"
    FREE_CITY = "free_city"
    EMBASSY = "embassy"


class FugitiveKind(StrEnum):
    OUTLAW = "outlaw"
    ACCUSED = "accused"
    DEFECTOR = "defector"
    RUNAWAY = "runaway"
    DESERTER = "deserter"
    HERETIC = "heretic"


class SanctuaryState(StrEnum):
    SHELTERED = "sheltered"
    NEGOTIATING = "negotiating"
    BESIEGED = "besieged"
    VIOLATED = "violated"
    ENDED = "ended"


class SatireSource(StrEnum):
    JESTER = "jester"
    ARTWORK = "artwork"
    MORTAL = "mortal"
    GOD = "god"
