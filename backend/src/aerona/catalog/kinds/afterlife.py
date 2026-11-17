from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.faith import StratumValence


@dataclass(frozen=True)
class StratumValenceSpec:
    floor_rule: str | None = None
    ceiling_rule: str | None = None


STRATUM_VALENCES: Mapping[StratumValence, StratumValenceSpec] = total(
    StratumValence,
    {
        StratumValence.REWARD: StratumValenceSpec(floor_rule="paradise_score"),
        StratumValence.NEUTRAL: StratumValenceSpec(),
        StratumValence.PUNISHMENT: StratumValenceSpec(ceiling_rule="torment_score"),
        StratumValence.MIXED: StratumValenceSpec(floor_rule="torment_score", ceiling_rule="paradise_score"),
    },
)
