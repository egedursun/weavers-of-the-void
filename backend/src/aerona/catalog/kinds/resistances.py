from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from aerona.core.total import total
from aerona.domain.enums.powers import ResistanceKind

Reads = Literal["devices", "willpower", "focus", "piety", "sanctity", "iron", "counter_power", "distance", "nothing", "disbelief", "ancestral"]


@dataclass(frozen=True)
class Resistance:
    reads: Reads
    share_pct: int


R = ResistanceKind
RESISTANCES: Mapping[ResistanceKind, Resistance] = total(
    ResistanceKind,
    {
        R.WILL: Resistance("willpower", 50),
        R.DISCIPLINE: Resistance("focus", 50),
        R.FAITH: Resistance("piety", 50),
        R.SANCTITY: Resistance("sanctity", 50),
        R.MATERIAL: Resistance("iron", 25),
        R.DAMPENER: Resistance("devices", 25),
        R.DISTANCE: Resistance("distance", 25),
        R.COUNTER_SOURCE: Resistance("counter_power", 25),
        R.NONE: Resistance("nothing", 0),
        R.DISBELIEF: Resistance("disbelief", 40),
        R.ANCESTRAL: Resistance("ancestral", 35),
    },
)
