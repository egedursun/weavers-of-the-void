from collections.abc import Mapping

from aerona.catalog.grief import OPEN_GRIEF_STAGES
from aerona.core.total import total
from aerona.domain.enums.mind import MemoryKind, NeedKind, RelationComponent, ThoughtKind
from aerona.domain.enums.mortal import DeathCause

OPEN_GRIEF = OPEN_GRIEF_STAGES


OPEN_STAGES = OPEN_GRIEF_STAGES


REMEMBERED: Mapping[RelationComponent, tuple[MemoryKind, ...]] = total(
    RelationComponent,
    {
        RelationComponent.TRADE: (MemoryKind.TRADED_WITH,),
        RelationComponent.KINSHIP: (MemoryKind.MARRIED_INTO,),
        RelationComponent.FAITH: (MemoryKind.CONVERTED_ME, MemoryKind.DESECRATED_HOLY),
        RelationComponent.WAR_MEMORY: (MemoryKind.FOUGHT_US, MemoryKind.CONQUERED_US, MemoryKind.KILLED_KIN),
        RelationComponent.HELP: (MemoryKind.FAMINE_AID, MemoryKind.SAVED_ME, MemoryKind.GIFTED_ME, MemoryKind.ALLIED_WITH),
        RelationComponent.INSULT: (MemoryKind.HUMILIATED_ME, MemoryKind.CHEATED_US, MemoryKind.SPIED_ON_US, MemoryKind.DEMANDED_TRIBUTE),
        RelationComponent.RIVALRY: (MemoryKind.ENVIED,),
        RelationComponent.LANGUAGE: (),
        RelationComponent.VALUES: (),
    },
)


BODILESS_NEEDS = (NeedKind.SUSTENANCE, NeedKind.DRINK)

GLORIOUS_SINCE_THOUGHT_KINDS = (ThoughtKind.WON_BATTLE, ThoughtKind.WON_DUEL)
KILLING_ACT_DEATH_CAUSES = frozenset({DeathCause.EXECUTION, DeathCause.SACRIFICE})
