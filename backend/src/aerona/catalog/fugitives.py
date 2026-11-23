from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.belonging import FugitiveKind, SanctuaryKind

F = FugitiveKind
K = SanctuaryKind


@dataclass(frozen=True)
class FugitiveSpec:
    label: str
    embassy: bool
    city_frees: bool
    hunt: str


@dataclass(frozen=True)
class SanctuarySpec:
    label: str
    hides: bool
    offence: str


FUGITIVES: Mapping[FugitiveKind, FugitiveSpec] = total(
    FugitiveKind,
    {
        F.OUTLAW: FugitiveSpec("Outlaw", False, False, "outlaw_hunt_pct"),
        F.ACCUSED: FugitiveSpec("Accused", True, False, "accused_hunt_pct"),
        F.DEFECTOR: FugitiveSpec("Defector", True, False, "defector_hunt_pct"),
        F.RUNAWAY: FugitiveSpec("Runaway from bondage", False, True, "runaway_hunt_pct"),
        F.DESERTER: FugitiveSpec("Deserter", False, False, "deserter_hunt_pct"),
        F.HERETIC: FugitiveSpec("Fled persecution", True, False, "heretic_hunt_pct"),
    },
)

SANCTUARIES: Mapping[SanctuaryKind, SanctuarySpec] = total(
    SanctuaryKind,
    {
        K.TEMPLE: SanctuarySpec("Temple", False, "desecration"),
        K.HOSPITALITY: SanctuarySpec("Hospitality", False, "broken hospitality"),
        K.ASYLUM: SanctuarySpec("Asylum", False, "broken asylum"),
        K.WILDS: SanctuarySpec("The wilds", True, "a hunt in the wilds"),
        K.FREE_CITY: SanctuarySpec("Free city", False, "a breach of the city's charter"),
        K.EMBASSY: SanctuarySpec("Embassy", False, "a crisis between powers"),
    },
)
