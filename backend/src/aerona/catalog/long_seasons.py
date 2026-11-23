from collections.abc import Callable
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.ages import LongSeasonReach, SeasonCause, SeasonSource, SeasonSpellShape

EQUATOR_BAND = 25
POLE_BAND = 60
MAP_MIDDLE = 0.5


def northern(map_y: float | None) -> bool:
    return map_y is None or map_y < MAP_MIDDLE


@dataclass(frozen=True)
class CauseSpec:
    label: str
    shapes: frozenset[SeasonSpellShape]
    source: SeasonSource | None


@dataclass(frozen=True)
class ReachSpec:
    label: str
    covers: Callable[[int, bool], bool]


CAUSES = total(
    SeasonCause,
    {
        SeasonCause.ORBIT: CauseSpec("Orbit", frozenset({SeasonSpellShape.CYCLING}), None),
        SeasonCause.NATURAL_LAW: CauseSpec("Natural law", frozenset({SeasonSpellShape.CYCLING}), None),
        SeasonCause.DIVINE: CauseSpec("A god", frozenset({SeasonSpellShape.CYCLING, SeasonSpellShape.SINGLE}), None),
        SeasonCause.IMPACT: CauseSpec("Impact", frozenset({SeasonSpellShape.SINGLE}), SeasonSource.IMPACT),
        SeasonCause.ERUPTION: CauseSpec("Eruption", frozenset({SeasonSpellShape.SINGLE}), SeasonSource.REGION),
        SeasonCause.STELLAR: CauseSpec("Its star", frozenset({SeasonSpellShape.SINGLE}), SeasonSource.STAR),
        SeasonCause.OCEAN_SHIFT: CauseSpec("A turned current", frozenset({SeasonSpellShape.SINGLE}), SeasonSource.REGION),
        SeasonCause.MADE: CauseSpec("Works of peoples", frozenset({SeasonSpellShape.SINGLE}), SeasonSource.INCIDENT),
    },
)
REACHES = total(
    LongSeasonReach,
    {
        LongSeasonReach.WORLD: ReachSpec("The whole world", lambda latitude, northern: True),
        LongSeasonReach.NORTH: ReachSpec("The northern half", lambda latitude, northern: northern),
        LongSeasonReach.SOUTH: ReachSpec("The southern half", lambda latitude, northern: not northern),
        LongSeasonReach.EQUATOR: ReachSpec("The equator", lambda latitude, northern: latitude <= EQUATOR_BAND),
        LongSeasonReach.POLES: ReachSpec("The poles", lambda latitude, northern: latitude >= POLE_BAND),
    },
)
