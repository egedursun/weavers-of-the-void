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
    MIND_LINK = "mind_link"
    BROADCAST = "broadcast"


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
    BEACON_CHAIN = "beacon_chain"
    OPTICAL_RELAY = "optical_relay"
    COURIER_POST = "courier_post"
    BOUND_PAIR = "bound_pair"
    WIRE_STATION = "wire_station"
    RADIO_STATION = "radio_station"
    MIND_LINK_STATION = "mind_link_station"
    GROWN_NODE = "grown_node"


class SignalState(StrEnum):
    ACTIVE = "active"
    CAPTURED = "captured"
    BURNED = "burned"
