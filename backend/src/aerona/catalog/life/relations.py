from collections.abc import Mapping

from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.mind import Facet, MemoryKind, ThoughtKind
from aerona.domain.enums.relations import GroupKind, InteractionKind, PassionKind, RelationType

BOND_OF = {
    RelationType.LOVER: BondKind.LOVES,
    RelationType.RIVAL: BondKind.RIVAL,
    RelationType.NEMESIS: BondKind.RIVAL,
    RelationType.ENEMY: BondKind.ENEMY,
    RelationType.BEST_FRIEND: BondKind.COMPANION,
    RelationType.CLOSE_FRIEND: BondKind.COMPANION,
}


MEMORY_PASSIONS = {
    MemoryKind.LAMENTED: PassionKind.GRIEF,
    MemoryKind.DREADS: PassionKind.FEAR,
    MemoryKind.HUMILIATED_ME: PassionKind.SHAME,
    MemoryKind.ENVIED: PassionKind.ENVY,
    MemoryKind.TAUGHT_ME: PassionKind.ADMIRATION,
}


CONFORMING = (Facet.COOPERATION, Facet.POLITENESS, Facet.SENSE_OF_DUTY)


GAIN_THOUGHTS = {RelationType.FRIEND: ThoughtKind.MADE_A_FRIEND, RelationType.LOVER: ThoughtKind.FELL_IN_LOVE, RelationType.CRUSH: ThoughtKind.FELL_IN_LOVE}


LOSS_THOUGHTS = {RelationType.FRIEND: ThoughtKind.LOST_A_FRIEND, RelationType.LOVER: ThoughtKind.HEARTBROKEN}


FACTION_GROUPS: Mapping[GroupKind, frozenset[FactionKind]] = {
    GroupKind.CELL: frozenset({FactionKind.SECRET_SOCIETY, FactionKind.ASSASSINS, FactionKind.REBELS}),
    GroupKind.BAND: frozenset(
        {FactionKind.BANDITS, FactionKind.ROUTE_RAIDERS, FactionKind.CRIME_FAMILY, FactionKind.THIEVES_GUILD, FactionKind.SMUGGLING_RING}
    ),
    GroupKind.TEAM: frozenset({FactionKind.CHARTERED_COMPANY, FactionKind.ENGINEERS_SOCIETY, FactionKind.SCHOLARS_ACADEMY, FactionKind.CLUB}),
}


WARM = (PassionKind.LOVE, PassionKind.LOYALTY)

ROMANTIC_KINDS_RELATION_TYPES = frozenset({RelationType.LOVER, RelationType.EX_LOVER})
WEIGHT_INTERACTION_KINDS = frozenset({InteractionKind.COMFORT, InteractionKind.ARGUE})
WEIGHT_INTERACTION_KINDS_2 = frozenset({InteractionKind.QUARREL, InteractionKind.BRAWL})
