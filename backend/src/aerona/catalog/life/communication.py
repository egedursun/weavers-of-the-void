from collections.abc import Mapping

from aerona.core.total import total
from aerona.domain.enums.communication import DispatchContent, Medium, SignalKind
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.networks import NetworkCarrier
from aerona.domain.enums.polity import OfficeKind

CARRIER_MEDIUM: Mapping[NetworkCarrier, Medium] = total(
    NetworkCarrier,
    {
        NetworkCarrier.RELAY: Medium.NETWORK,
        NetworkCarrier.WIRED: Medium.NETWORK,
        NetworkCarrier.BROADCAST: Medium.BROADCAST,
        NetworkCarrier.MESH: Medium.NETWORK,
        NetworkCarrier.MIND_LINK: Medium.MIND_LINK,
        NetworkCarrier.RITE_LINK: Medium.NETWORK,
        NetworkCarrier.GROWN_LINK: Medium.NETWORK,
        NetworkCarrier.DREAM_LINK: Medium.DREAM,
    },
)


MEDIUM_RANK = (Medium.MIND_LINK, Medium.BROADCAST, Medium.NETWORK)


SPEED_RULES = {
    Medium.ENVOY: "envoy_hops",
    Medium.LETTER: "letter_hops",
    Medium.HERALD: "herald_hops",
    Medium.BIRD: "bird_hops",
    Medium.SIGNAL_FIRE: "signal_fire_hops",
}


TEXTS = {
    DispatchContent.PROPOSAL: "a proposal",
    DispatchContent.DEMAND: "a demand",
    DispatchContent.THREAT: "a threat",
    DispatchContent.INSULT: "an insult",
    DispatchContent.GIFT_NOTICE: "word of a gift",
    DispatchContent.DECLARATION: "a declaration",
    DispatchContent.REPORT: "a report",
    DispatchContent.PLEA: "a plea",
    DispatchContent.INTELLIGENCE: "intelligence",
    DispatchContent.ORDER: "an order",
    DispatchContent.WARNING: "a warning",
}


CUT_WHEN_TAKEN = total(
    SignalKind,
    {
        SignalKind.BEACON_CHAIN: False,
        SignalKind.OPTICAL_RELAY: False,
        SignalKind.COURIER_POST: True,
        SignalKind.BOUND_PAIR: False,
        SignalKind.WIRE_STATION: True,
        SignalKind.RADIO_STATION: False,
        SignalKind.MIND_LINK_STATION: False,
        SignalKind.GROWN_NODE: True,
    },
)

WELCOME_SKILL_KINDS = (SkillKind.NEGOTIATION, SkillKind.ETIQUETTE)
EFFECTS_DISPATCH_CONTENTS = frozenset({DispatchContent.REPORT, DispatchContent.INTELLIGENCE})
COURTESIES_OFFICE_KINDS = (OfficeKind.AMBASSADOR, OfficeKind.CHANCELLOR)
