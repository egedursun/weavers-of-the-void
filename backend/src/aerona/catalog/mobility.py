from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_depth import MobilityEvent

M = MobilityEvent
C = SocialClass


@dataclass(frozen=True)
class MobilitySpec:
    label: str
    rises: bool
    lands_in: SocialClass | None = None
    from_classes: frozenset[SocialClass] = frozenset()


MOBILITY_EVENTS: Mapping[MobilityEvent, MobilitySpec] = total(
    MobilityEvent,
    {
        M.ENNOBLED: MobilitySpec("Raised among the nobles", rises=True, lands_in=C.NOBLE),
        M.ENSLAVED: MobilitySpec("Put in chains", rises=False, lands_in=C.SERF_OR_SLAVE),
        M.FREED: MobilitySpec("Set free", rises=True),
        M.RUINED: MobilitySpec("Ruined", rises=False),
        M.ENRICHED: MobilitySpec(
            "Risen by wealth", rises=True, lands_in=C.MERCHANT, from_classes=frozenset({C.FARMER, C.ARTISAN, C.WORKER, C.UNEMPLOYED, C.CITIZEN})
        ),
        M.ORDAINED: MobilitySpec("Ordained", rises=True, lands_in=C.PRIEST),
        M.OUTCAST: MobilitySpec("Cast out", rises=False, lands_in=C.OUTCAST),
    },
)
