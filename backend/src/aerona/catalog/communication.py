from aerona.domain.enums.communication import DispatchContent, DispatchState, EnvoyFate, Medium, OpinionSubject, SignalKind, SignalState

MEDIUM_LABELS: dict[Medium, str] = {
    Medium.ENVOY: "Envoy",
    Medium.LETTER: "Letter",
    Medium.HERALD: "Herald",
    Medium.SIGNAL_FIRE: "Signal fire",
    Medium.DREAM: "Dream",
    Medium.BIRD: "Messenger bird",
    Medium.MAGIC_SENDING: "Magic sending",
    Medium.NETWORK: "By network",
    Medium.MIND_LINK: "By a link between minds",
    Medium.BROADCAST: "By broadcast",
}
CONTENT_LABELS: dict[DispatchContent, str] = {
    DispatchContent.PROPOSAL: "A proposal",
    DispatchContent.DEMAND: "A demand",
    DispatchContent.THREAT: "A threat",
    DispatchContent.INSULT: "An insult",
    DispatchContent.GIFT_NOTICE: "Word of a gift",
    DispatchContent.DECLARATION: "A declaration",
    DispatchContent.REPORT: "A report",
    DispatchContent.PLEA: "A plea",
    DispatchContent.INTELLIGENCE: "Intelligence",
}
STATE_LABELS: dict[DispatchState, str] = {
    DispatchState.UNDER_WAY: "On its way",
    DispatchState.DELIVERED: "Delivered",
    DispatchState.INTERCEPTED: "Intercepted",
    DispatchState.LOST: "Lost on the road",
}
ENVOY_LABELS: dict[EnvoyFate, str] = {
    EnvoyFate.RECEIVED: "Received with courtesy",
    EnvoyFate.INSULTED: "Insulted",
    EnvoyFate.IMPRISONED: "Thrown in chains",
    EnvoyFate.KILLED: "Slain",
}
SUBJECT_LABELS: dict[OpinionSubject, str] = {
    OpinionSubject.RULER: "Ruler",
    OpinionSubject.LAW: "Law",
    OpinionSubject.WAR: "War",
    OpinionSubject.GOD: "God",
    OpinionSubject.IDEOLOGY: "Creed",
}
SIGNAL_LABELS: dict[SignalKind, str] = {
    SignalKind.BEACON_CHAIN: "Beacon chains",
    SignalKind.OPTICAL_RELAY: "Optical relays",
    SignalKind.COURIER_POST: "Courier posts",
    SignalKind.BOUND_PAIR: "Bound pairs",
    SignalKind.WIRE_STATION: "Wire stations",
    SignalKind.RADIO_STATION: "Radio stations",
    SignalKind.MIND_LINK_STATION: "Mind-link stations",
    SignalKind.GROWN_NODE: "Grown nodes",
}
SIGNAL_STATE_LABELS: dict[SignalState, str] = {
    SignalState.ACTIVE: "Standing",
    SignalState.CAPTURED: "Captured",
    SignalState.BURNED: "Burned",
}
MORTAL_MEDIA = frozenset({Medium.ENVOY, Medium.LETTER, Medium.HERALD, Medium.BIRD, Medium.SIGNAL_FIRE, Medium.NETWORK})
