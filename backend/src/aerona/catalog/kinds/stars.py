from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.cosmography import StarAge


@dataclass(frozen=True)
class StarAgeSpec:
    radiation_rule: str | None
    stability_rule: str
    length_rule: str | None
    lasts: bool = True


A = StarAge
STAR_AGES: Mapping[StarAge, StarAgeSpec] = total(
    StarAge,
    {
        A.YOUNG: StarAgeSpec("young_radiation", "young_stability", "young_pct"),
        A.MAIN: StarAgeSpec("main_radiation", "main_stability", None),
        A.OLD: StarAgeSpec("main_radiation", "old_stability", "old_pct"),
        A.DYING: StarAgeSpec("dying_radiation", "dying_stability", "dying_pct"),
        A.DEAD: StarAgeSpec(None, "main_stability", None, lasts=False),
        A.REBORN: StarAgeSpec("young_radiation", "young_stability", "young_pct"),
    },
)
