from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.agrarian import PreparednessKind, RebuildCause, RebuildPlan
from aerona.domain.enums.culture import Technique

C = RebuildCause
P = RebuildPlan
K = PreparednessKind


@dataclass(frozen=True)
class CauseSpec:
    label: str
    lesson: PreparednessKind
    chance: str
    technique: Technique | None = None


@dataclass(frozen=True)
class PlanSpec:
    label: str
    moves: bool
    leaves: bool
    builds: bool


REBUILD_CAUSES: Mapping[RebuildCause, CauseSpec] = total(
    RebuildCause,
    {
        C.FIRE: CauseSpec("Fire", K.FIREBREAK, "fire_lesson_pct"),
        C.FLOOD: CauseSpec("Flood", K.LEVEE, "flood_lesson_pct"),
        C.QUAKE: CauseSpec("Earthquake", K.DRILL, "quake_lesson_pct"),
        C.STORM: CauseSpec("Storm", K.SHELTERS, "storm_lesson_pct"),
        C.SACK: CauseSpec("Sack", K.WATCHTOWER, "sack_lesson_pct"),
        C.ERUPTION: CauseSpec("Eruption", K.EVACUATION_ROUTES, "eruption_lesson_pct"),
        C.SEA_WAVE: CauseSpec("Sea wave", K.SEAWALL, "sea_wave_lesson_pct"),
        C.LANDSLIDE: CauseSpec("Landslide", K.WARNING_NETWORK, "landslide_lesson_pct", Technique.TERRACING),
        C.SINKHOLE: CauseSpec("Sinkhole", K.QUAKE_BUILDING, "sinkhole_lesson_pct"),
        C.PLAGUE: CauseSpec("Plague", K.IMMUNISATION_PLAN, "plague_lesson_pct"),
    },
)

REBUILD_PLANS: Mapping[RebuildPlan, PlanSpec] = total(
    RebuildPlan,
    {
        P.PLANNED: PlanSpec("Planned", False, False, True),
        P.OPPORTUNISTIC: PlanSpec("Opportunistic", False, False, True),
        P.RELOCATED: PlanSpec("Relocated", True, True, True),
        P.ABANDONED: PlanSpec("Abandoned", False, True, False),
        P.RESTORED: PlanSpec("Restored as it was", False, False, True),
    },
)
