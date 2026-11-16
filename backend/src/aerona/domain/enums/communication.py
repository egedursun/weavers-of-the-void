from enum import StrEnum


class Medium(StrEnum):
    ENVOY = "envoy"
    LETTER = "letter"
    HERALD = "herald"
    SIGNAL_FIRE = "signal_fire"
    DREAM = "dream"
    BIRD = "bird"
    MAGIC_SENDING = "magic_sending"
    NETWORK = "network"


class DispatchContent(StrEnum):
    PROPOSAL = "proposal"
    DEMAND = "demand"
    THREAT = "threat"
    INSULT = "insult"
    GIFT_NOTICE = "gift_notice"
    DECLARATION = "declaration"
    REPORT = "report"
    PLEA = "plea"
    INTELLIGENCE = "intelligence"


class DispatchState(StrEnum):
    UNDER_WAY = "under_way"
    DELIVERED = "delivered"
    INTERCEPTED = "intercepted"
    LOST = "lost"


class EnvoyFate(StrEnum):
    RECEIVED = "received"
    INSULTED = "insulted"
    IMPRISONED = "imprisoned"
    KILLED = "killed"


class OpinionSubject(StrEnum):
    RULER = "ruler"
    LAW = "law"
    WAR = "war"
    GOD = "god"
    IDEOLOGY = "ideology"


class SignalKind(StrEnum):
    FIRE_BEACON = "fire_beacon"
    MIRROR_TOWER = "mirror_tower"
    POST_STATION = "post_station"
    SENDING_STONE = "sending_stone"


class SignalState(StrEnum):
    ACTIVE = "active"
    CAPTURED = "captured"
    BURNED = "burned"
