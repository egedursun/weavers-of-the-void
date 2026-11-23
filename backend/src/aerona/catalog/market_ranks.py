from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.agrarian import CentralityRank
from aerona.rules.registry import Rules

Number = Callable[[Rules], int]


@dataclass(frozen=True)
class RankSpec:
    order: int
    threshold: Number
    reach: Number
    centrality: Number
    goal: Number
    market: bool
    fair: bool = False
    unique: bool = False


RANKS: Mapping[CentralityRank, RankSpec] = total(
    CentralityRank,
    {
        CentralityRank.DAILY: RankSpec(0, lambda rules: 0, lambda rules: 0, lambda rules: 0, lambda rules: rules.central_places.weekly_threshold, market=False),
        CentralityRank.WEEKLY: RankSpec(
            1,
            lambda rules: rules.central_places.weekly_threshold,
            lambda rules: rules.central_places.weekly_range,
            lambda rules: rules.central_places.weekly_centrality,
            lambda rules: rules.central_places.rare_threshold,
            market=True,
        ),
        CentralityRank.SEASONAL: RankSpec(
            2,
            lambda rules: rules.central_places.seasonal_threshold,
            lambda rules: rules.central_places.seasonal_range * rules.central_places.fair_reach_pct // 100,
            lambda rules: rules.central_places.seasonal_centrality,
            lambda rules: rules.central_places.rare_threshold,
            market=True,
            fair=True,
        ),
        CentralityRank.RARE: RankSpec(
            3,
            lambda rules: rules.central_places.rare_threshold,
            lambda rules: rules.central_places.rare_range,
            lambda rules: rules.central_places.rare_centrality,
            lambda rules: rules.central_places.metropolitan_threshold,
            market=True,
        ),
        CentralityRank.METROPOLITAN: RankSpec(
            4,
            lambda rules: rules.central_places.metropolitan_threshold,
            lambda rules: rules.central_places.metropolitan_range,
            lambda rules: rules.central_places.metropolitan_centrality,
            lambda rules: rules.central_places.metropolitan_threshold * 2,
            market=True,
            unique=True,
        ),
    },
)


def by_order(*, descending: bool = False) -> list[CentralityRank]:
    return sorted(RANKS, key=lambda rank: RANKS[rank].order, reverse=descending)


def higher_markets(rank: CentralityRank) -> frozenset[CentralityRank]:
    return frozenset(other for other, spec in RANKS.items() if spec.market and spec.order > RANKS[rank].order)


def widest_reach(rules: Rules) -> int:
    return max(spec.reach(rules) for spec in RANKS.values())
