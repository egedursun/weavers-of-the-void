from enum import StrEnum


class NetworkCarrier(StrEnum):
    RELAY = "relay"
    WIRED = "wired"
    BROADCAST = "broadcast"
    MESH = "mesh"
    MIND_LINK = "mind_link"
    RITE_LINK = "rite_link"
    GROWN_LINK = "grown_link"


class NetworkAccess(StrEnum):
    CLOSED = "closed"
    MEMBERS = "members"
    LICENSED = "licensed"
    OPEN = "open"


class NetworkRole(StrEnum):
    HUB = "hub"
    STATION = "station"
    END = "end"
    RELAY = "relay"
    ARCHIVE = "archive"


class OutageCause(StrEnum):
    STORM = "storm"
    FLARE = "flare"
    WAR = "war"
    SABOTAGE = "sabotage"
    INTRUSION = "intrusion"
    DECAY = "decay"
    RITE = "rite"
    POWER = "power"
    SHORTAGE = "shortage"
    DIVINE = "divine"
