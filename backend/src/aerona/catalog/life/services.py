from collections.abc import Callable

from aerona.domain.enums.constructs import ContractStatus
from aerona.domain.enums.cycles import GiftState
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.mind import DreamKind, MemoryKind, ThoughtKind
from aerona.domain.enums.records import WitnessMode
from aerona.domain.enums.speech import SpeechVenue
from aerona.domain.enums.structure import ConstructionState, StructureKind
from aerona.domain.enums.urban import ZoneKind
from aerona.domain.enums.war import WarEnding
from aerona.rules.registry import Rules

RELATION_EFFECTS: dict[WarEnding, Callable[[Rules], int]] = {
    WarEnding.CONQUEST: lambda rules: -rules.campaigns.conquest_relation,
    WarEnding.TRIBUTE: lambda rules: -rules.campaigns.tribute_relation,
    WarEnding.WHITE_PEACE: lambda rules: rules.campaigns.white_peace_relation,
    WarEnding.EXHAUSTION: lambda rules: rules.diplomacy.exhaustion_peace_relation,
    WarEnding.PEACE: lambda rules: rules.diplomacy.peace_relation,
    WarEnding.MIRACLE: lambda rules: rules.diplomacy.peace_relation,
}


ENDING_MEMORIES: dict[WarEnding, MemoryKind] = {
    WarEnding.VICTORY: MemoryKind.HUMILIATED_ME,
    WarEnding.CONQUEST: MemoryKind.CONQUERED_US,
    WarEnding.TRIBUTE: MemoryKind.DEMANDED_TRIBUTE,
    WarEnding.EXHAUSTION: MemoryKind.MADE_PEACE,
    WarEnding.PEACE: MemoryKind.MADE_PEACE,
    WarEnding.WHITE_PEACE: MemoryKind.MADE_PEACE,
    WarEnding.BETRAYAL: MemoryKind.BETRAYED_ME,
    WarEnding.MIRACLE: MemoryKind.DIVINE_WILL,
}


ENDING_LABELS: dict[WarEnding, str] = {
    WarEnding.VICTORY: "victory",
    WarEnding.CONQUEST: "conquest",
    WarEnding.TRIBUTE: "tribute",
    WarEnding.EXHAUSTION: "exhaustion peace",
    WarEnding.PEACE: "peace",
    WarEnding.WHITE_PEACE: "white peace",
    WarEnding.BETRAYAL: "betrayal",
    WarEnding.SAME_FRONT: "front of the same war",
    WarEnding.NO_SIDE_LEFT: "no side left",
    WarEnding.MIRACLE: "peace miracle",
    WarEnding.MEDIATED: "mediated peace",
}


ZONE_INK: dict[ZoneKind, str] = {
    ZoneKind.GOVERNANCE: "#c9a240",
    ZoneKind.RESIDENTIAL: "#c9744f",
    ZoneKind.COMMERCIAL: "#5d8fc4",
    ZoneKind.INDUSTRIAL: "#8a74a8",
    ZoneKind.AGRICULTURAL: "#b5b85a",
    ZoneKind.CIVIC: "#4f9fa6",
    ZoneKind.GREEN: "#4f9a5a",
    ZoneKind.TRANSPORT: "#7a8a96",
    ZoneKind.PORT: "#4f7e9c",
    ZoneKind.MILITARY: "#a0524a",
    ZoneKind.RESEARCH: "#6a7fc0",
}


STATE_OPACITY: dict[ConstructionState, float] = {
    ConstructionState.PLANNED: 0.35,
    ConstructionState.BUILDING: 0.6,
    ConstructionState.COMPLETE: 1.0,
    ConstructionState.DAMAGED: 0.7,
    ConstructionState.RUINED: 0.3,
    ConstructionState.ABANDONED: 0.25,
    ConstructionState.DISMANTLED: 0.1,
    ConstructionState.RESTORED: 1.0,
}


BUILDING_STATES = (
    frozenset({ConstructionState.COMPLETE}),
    frozenset({ConstructionState.PLANNED, ConstructionState.BUILDING}),
    frozenset({ConstructionState.DAMAGED}),
    frozenset({ConstructionState.RUINED, ConstructionState.ABANDONED, ConstructionState.DISMANTLED}),
)


OPEN = (ContractStatus.POSTED, ContractStatus.TAKEN)


VENUE_STRUCTURES = {
    SpeechVenue.TEMPLE: frozenset({StructureKind.TEMPLE, StructureKind.SHRINE, StructureKind.MONASTERY}),
    SpeechVenue.SCHOOL: frozenset({StructureKind.SCHOOL, StructureKind.ACADEMY, StructureKind.UNIVERSITY}),
}


PRESENT_MODES = (WitnessMode.SAW, WitnessMode.TOOK_PART)


DREAM_THOUGHTS = {
    DreamKind.ORDINARY: ThoughtKind.HAD_GOOD_DREAM,
    DreamKind.NIGHTMARE: ThoughtKind.HAD_NIGHTMARE,
    DreamKind.LONGING: ThoughtKind.DREAMED_OF_LONGING,
    DreamKind.PROPHETIC: ThoughtKind.RECEIVED_VISITATION,
    DreamKind.VISITATION: ThoughtKind.RECEIVED_VISITATION,
    DreamKind.SHARED: ThoughtKind.HAD_GOOD_DREAM,
    DreamKind.LUCID: ThoughtKind.HAD_GOOD_DREAM,
    DreamKind.MEMORY: ThoughtKind.DREAMED_OF_LONGING,
}

DISBAND_FACTION_FACTION_KINDS = (FactionKind.WANDERING_MARKET, FactionKind.ROUTE_RAIDERS)
MEND_CYCLE_LINKS_GIFT_STATES = (GiftState.OPEN, GiftState.DESTROYED)
SECRET_FACTION_KINDS = frozenset({FactionKind.CRAFT_GUILD, FactionKind.MERCHANT_GUILD})
