from enum import StrEnum


class HiddenTruthKind(StrEnum):
    EXISTENCE = "existence"
    NATURE = "nature"
    PRESENCE = "presence"
    POWER = "power"
    EVENT = "event"
    ORIGIN = "origin"
    AWAKENING = "awakening"
    PROGRAMME = "programme"
    COSMIC = "cosmic"
    LOCATION = "location"
    LINEAGE = "lineage"


class ConcealScope(StrEnum):
    EVERYONE = "everyone"
    A_PEOPLE = "a_people"
    A_POLITY = "a_polity"
    THE_UNINITIATED = "the_uninitiated"
    A_WORLD = "a_world"
    THE_COSMOS = "the_cosmos"
    A_HOUSE = "a_house"
    A_FAITH = "a_faith"


class KeeperRole(StrEnum):
    ENFORCER = "enforcer"
    GUARDIAN = "guardian"
    MEMBER = "member"
    PATRON = "patron"
    ARCHIVIST = "archivist"
    GO_BETWEEN = "go_between"


class SeekerAim(StrEnum):
    EXPOSE = "expose"
    EXPLOIT = "exploit"
    DESTROY_THE_HIDDEN = "destroy_the_hidden"
    JOIN_THE_HIDDEN = "join_the_hidden"
    UNDERSTAND = "understand"
    PROTECT = "protect"


class TruthAttitude(StrEnum):
    UNKNOWN = "unknown"
    RUMOURED = "rumoured"
    DENIED = "denied"
    FEARED = "feared"
    REVERED = "revered"
    ACCEPTED = "accepted"
    EXPLOITED = "exploited"
    PROTECTED = "protected"
    BARGAINED = "bargained"


class BreachCause(StrEnum):
    OVERT_USE = "overt_use"
    WITNESS = "witness"
    DEFECTOR = "defector"
    INVESTIGATOR = "investigator"
    ACCIDENT = "accident"
    WAR = "war"
    RECORD_LEAK = "record_leak"
    INTRUSION = "intrusion"
    REVELATION_BY_GOD = "revelation_by_god"
    CHILDREN = "children"
    DREAMS = "dreams"
    EXCAVATION = "excavation"


class KeeperResponse(StrEnum):
    NONE = "none"
    COVER_STORY = "cover_story"
    MEMORY_REMOVAL = "memory_removal"
    DISCREDITING = "discrediting"
    LAW = "law"
    SILENCING = "silencing"
    BARGAIN = "bargain"
    RELOCATION = "relocation"
