from aerona.domain.enums.communication import DispatchContent, DispatchState, EnvoyFate, Medium, OpinionSubject, SignalKind, SignalState

MEDIUM_LABELS: dict[Medium, str] = {
    Medium.ENVOY: "Envoy",
    Medium.LETTER: "Letter",
    Medium.HERALD: "Herald",
    Medium.SIGNAL_FIRE: "Signal fire",
    Medium.DREAM: "Dream",
    Medium.BIRD: "Messenger bird",
    Medium.MAGIC_SENDING: "Magic sending",
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
    SignalKind.FIRE_BEACON: "Fire beacons",
    SignalKind.MIRROR_TOWER: "Mirror towers",
    SignalKind.POST_STATION: "Post stations",
    SignalKind.SENDING_STONE: "Sending stones",
}
SIGNAL_STATE_LABELS: dict[SignalState, str] = {
    SignalState.ACTIVE: "Standing",
    SignalState.CAPTURED: "Captured",
    SignalState.BURNED: "Burned",
}
