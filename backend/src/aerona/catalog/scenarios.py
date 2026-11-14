from collections.abc import Callable
from dataclasses import dataclass

from aerona.core.grammar import an, several
from aerona.domain.enums.meta import ScenarioKey
from aerona.rules.registry import Rules

PERCENT = 100


@dataclass(frozen=True)
class ScenarioSpec:
    key: ScenarioKey
    name: Callable[[Rules], str]
    description: Callable[[Rules], str]
    points: Callable[[Rules], int]


def doom_limit(rules: Rules) -> int:
    return round(max(1, rules.balance.apocalypse_threshold) * rules.goals.keep_apocalypse_away_pct / PERCENT)


SCENARIOS: dict[ScenarioKey, ScenarioSpec] = {
    spec.key: spec
    for spec in (
        ScenarioSpec(
            ScenarioKey.DOOM_FAR,
            lambda rules: f"Keep doomsday away for {several(rules.goals.keep_apocalypse_away_epochs, 'epoch', 'epochs')}",
            lambda rules: f"The doomsday clock must never reach {doom_limit(rules)} for {several(rules.goals.keep_apocalypse_away_epochs, 'epoch', 'epochs')}.",
            lambda rules: rules.goals.keep_apocalypse_away_points,
        ),
        ScenarioSpec(
            ScenarioKey.ONE_FAITH,
            lambda rules: "Unite all peoples in one faith",
            lambda rules: (
                f"Every people in the world worships the same god (a son or you); at least {several(rules.goals.one_faith_min_peoples, 'people', 'peoples')}."
            ),
            lambda rules: rules.goals.one_faith_points,
        ),
        ScenarioSpec(
            ScenarioKey.LOST_STAR,
            lambda rules: "Rekindle the lost star",
            lambda rules: "A dead star or black sun burns again.",
            lambda rules: rules.goals.lost_star_points,
        ),
        ScenarioSpec(
            ScenarioKey.MANY_WORLDS,
            lambda rules: f"{an(rules.goals.inhabited_worlds, capital=True)}-world cosmos",
            lambda rules: f"At least {several(rules.goals.inhabited_worlds, 'world', 'worlds')} in the cosmos, each with a living people.",
            lambda rules: rules.goals.multiworld_points,
        ),
        ScenarioSpec(
            ScenarioKey.LONG_PEACE,
            lambda rules: f"{several(rules.goals.peace_epochs, 'epoch', 'epochs')} of peace",
            lambda rules: f"No war stays open for {rules.goals.peace_epochs} consecutive epochs.",
            lambda rules: rules.goals.peace_points,
        ),
        ScenarioSpec(
            ScenarioKey.COSMIC_POWER,
            lambda rules: "A civilization reaching for the stars",
            lambda rules: f"A people reaches civilization tier {rules.goals.cosmic_stage} (interstellar power).",
            lambda rules: rules.goals.cosmic_points,
        ),
        ScenarioSpec(
            ScenarioKey.LOYAL_PANTHEON,
            lambda rules: "A loyal pantheon",
            lambda rules: (
                f"No son rebels for {several(rules.goals.loyal_epochs, 'epoch', 'epochs')}; "
                f"at the end every son's loyalty is above {rules.goals.loyal_min_loyalty}."
            ),
            lambda rules: rules.goals.loyal_points,
        ),
        ScenarioSpec(
            ScenarioKey.NEW_HORIZONS,
            lambda rules: f"{rules.goals.horizon_lands} new lands",
            lambda rules: (
                f"{rules.goals.horizon_lands} new lands enter the map (at least {several(rules.goals.horizon_regions, 'region', 'regions')}): "
                "by mortal discovery, by the sons or by your hand."
            ),
            lambda rules: rules.goals.horizon_points,
        ),
    )
}
