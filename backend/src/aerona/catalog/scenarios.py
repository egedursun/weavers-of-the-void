from collections.abc import Callable
from dataclasses import dataclass

from aerona.catalog.goal_metrics import METRICS
from aerona.constants.units import PERCENT
from aerona.core.grammar import agree, an, several
from aerona.domain.enums.entity import CivilizationTier
from aerona.domain.enums.meta import GoalBasis, GoalCategory, GoalComparator, GoalMetric, ScenarioKey, ScenarioStatus
from aerona.rules.registry import Rules

ROMAN_NUMERALS = (
    (1000, "M"),
    (900, "CM"),
    (500, "D"),
    (400, "CD"),
    (100, "C"),
    (90, "XC"),
    (50, "L"),
    (40, "XL"),
    (10, "X"),
    (9, "IX"),
    (5, "V"),
    (4, "IV"),
    (1, "I"),
)


def roman(number: int) -> str:
    left, text = max(1, number), ""
    for value, symbol in ROMAN_NUMERALS:
        while left >= value:
            text += symbol
            left -= value
    return text


@dataclass(frozen=True)
class ScenarioSpec:
    key: ScenarioKey
    category: GoalCategory
    title: Callable[[int], str]
    describe: Callable[[Rules, int], str]
    default_target: Callable[[Rules], int]
    step: Callable[[Rules], int]
    points: Callable[[Rules], int]
    metrics: tuple[GoalMetric, ...] = ()
    basis: GoalBasis = GoalBasis.TOTAL
    stage_bound: bool = False

    def name(self, target: int, tier: int = 1) -> str:
        return self.title(target) if tier <= 1 else f"{self.title(target)} {roman(tier)}"

    def description(self, rules: Rules, target: int) -> str:
        return self.describe(rules, target)

    def target_for_tier(self, rules: Rules, tier: int) -> int:
        return min(self.target_max(rules), self.default_target(rules) + max(0, tier - 1) * self.step(rules))

    def target_max(self, rules: Rules) -> int:
        return int(max(CivilizationTier)) if self.stage_bound else rules.goals.scenario_target_max


def doom_limit(rules: Rules) -> int:
    return round(max(1, rules.balance.apocalypse_threshold) * rules.goals.keep_apocalypse_away_pct / PERCENT)


def epochs(count: int) -> str:
    return several(count, "epoch", "epochs")


def custom_title(metric: GoalMetric, comparator: GoalComparator, basis: GoalBasis, target: int) -> str:
    spec = METRICS[metric]
    if basis is GoalBasis.GAINED:
        return f"Gain {spec.count(target)}"
    bound = "At least" if comparator is GoalComparator.AT_LEAST else "At most"
    return f"{bound} {spec.count(target)}"


def custom_description(metric: GoalMetric, comparator: GoalComparator, basis: GoalBasis, target: int, hold_epochs: int) -> str:
    spec = METRICS[metric]
    if basis is GoalBasis.GAINED:
        reach = f"{spec.label}: {target} more than when the goal began"
    else:
        reach = f"{spec.label}: {'at least' if comparator is GoalComparator.AT_LEAST else 'at most'} {target}"
    return f"{reach}, held for {epochs(hold_epochs)}." if hold_epochs else f"{reach}."


S = ScenarioKey
C = GoalCategory
M = GoalMetric

SCENARIOS: dict[ScenarioKey, ScenarioSpec] = {
    spec.key: spec
    for spec in (
        ScenarioSpec(
            S.DOOM_FAR,
            C.TIME,
            lambda target: f"Keep doomsday away for {epochs(target)}",
            lambda rules, target: f"The doomsday clock must never reach {doom_limit(rules)} for {epochs(target)}.",
            lambda rules: rules.goals.keep_apocalypse_away_epochs,
            lambda rules: rules.goals.keep_apocalypse_away_step,
            lambda rules: rules.goals.keep_apocalypse_away_points,
        ),
        ScenarioSpec(
            S.ONE_FAITH,
            C.FAITH,
            lambda target: "Unite all peoples in one faith",
            lambda rules, target: f"Every people in the world worships the same god (a son or you); at least {several(target, 'people', 'peoples')}.",
            lambda rules: rules.goals.one_faith_min_peoples,
            lambda rules: rules.goals.one_faith_step,
            lambda rules: rules.goals.one_faith_points,
        ),
        ScenarioSpec(
            S.LOST_STAR,
            C.COSMOS,
            lambda target: "Rekindle the lost star" if target == 1 else f"Rekindle {several(target, 'lost star', 'lost stars')}",
            lambda rules, target: f"{several(target, 'dead star or black sun', 'dead stars or black suns')} {agree(target, 'burns', 'burn')} again.",
            lambda rules: rules.goals.lost_star_stars,
            lambda rules: rules.goals.lost_star_step,
            lambda rules: rules.goals.lost_star_points,
            metrics=(M.REBORN_STARS,),
            basis=GoalBasis.GAINED,
        ),
        ScenarioSpec(
            S.MANY_WORLDS,
            C.COSMOS,
            lambda target: f"{an(target, capital=True)}-world cosmos",
            lambda rules, target: f"At least {several(target, 'world', 'worlds')} in the cosmos, each with a living people.",
            lambda rules: rules.goals.inhabited_worlds,
            lambda rules: rules.goals.inhabited_worlds_step,
            lambda rules: rules.goals.multiworld_points,
            metrics=(M.INHABITED_WORLDS,),
        ),
        ScenarioSpec(
            S.LONG_PEACE,
            C.ORDER,
            lambda target: f"{epochs(target)} of peace",
            lambda rules, target: f"No war stays open for {epochs(target)} in a row.",
            lambda rules: rules.goals.peace_epochs,
            lambda rules: rules.goals.peace_step,
            lambda rules: rules.goals.peace_points,
        ),
        ScenarioSpec(
            S.COSMIC_POWER,
            C.PEOPLES,
            lambda target: "A civilization reaching for the stars",
            lambda rules, target: f"A people reaches civilization stage {target}.",
            lambda rules: rules.goals.cosmic_stage,
            lambda rules: rules.goals.cosmic_step,
            lambda rules: rules.goals.cosmic_points,
            metrics=(M.HIGHEST_CIV_TIER,),
            stage_bound=True,
        ),
        ScenarioSpec(
            S.LOYAL_PANTHEON,
            C.PANTHEON,
            lambda target: "A loyal pantheon",
            lambda rules, target: f"No son rebels for {epochs(target)}; at the end every son's loyalty is above {rules.goals.loyal_min_loyalty}.",
            lambda rules: rules.goals.loyal_epochs,
            lambda rules: rules.goals.loyal_step,
            lambda rules: rules.goals.loyal_points,
        ),
        ScenarioSpec(
            S.NEW_HORIZONS,
            C.DISCOVERY,
            lambda target: several(target, "new land", "new lands").capitalize(),
            lambda rules, target: (
                f"{several(target, 'new land enters', 'new lands enter')} the map "
                f"(at least {several(min(target, rules.goals.horizon_regions), 'region', 'regions')}): by mortal discovery, by the sons or by your hand."
            ),
            lambda rules: rules.goals.horizon_lands,
            lambda rules: rules.goals.horizon_step,
            lambda rules: rules.goals.horizon_points,
        ),
        ScenarioSpec(
            S.GOLDEN_AGE,
            C.PEOPLES,
            lambda target: "A golden age" if target == 1 else f"{several(target, 'golden age', 'golden ages')} at once",
            lambda rules, target: f"{several(target, 'community lives', 'communities live')} in a golden age at the same time.",
            lambda rules: rules.goals.golden_age_count,
            lambda rules: rules.goals.golden_age_step,
            lambda rules: rules.goals.golden_age_points,
            metrics=(M.GOLDEN_AGES,),
        ),
        ScenarioSpec(
            S.AGE_OF_WONDERS,
            C.CULTURE,
            lambda target: "An age of wonders",
            lambda rules, target: f"{several(target, 'new wonder rises', 'new wonders rise')} after the goal begins.",
            lambda rules: rules.goals.wonders_count,
            lambda rules: rules.goals.wonders_step,
            lambda rules: rules.goals.wonders_points,
            metrics=(M.WONDERS,),
            basis=GoalBasis.GAINED,
        ),
        ScenarioSpec(
            S.BRIDGE_THE_GALAXIES,
            C.SCALES,
            lambda target: "Bridge the galaxies",
            lambda rules, target: f"{several(target, 'voyage arrives', 'voyages arrive')} beyond a galaxy after the goal begins.",
            lambda rules: rules.goals.far_voyages_count,
            lambda rules: rules.goals.far_voyages_step,
            lambda rules: rules.goals.far_voyages_points,
            metrics=(M.FAR_VOYAGES,),
            basis=GoalBasis.GAINED,
        ),
        ScenarioSpec(
            S.AGE_OF_LEARNING,
            C.CULTURE,
            lambda target: "An age of learning",
            lambda rules, target: f"{several(target, 'new knowledge or theory appears', 'new knowledge and theories appear')} after the goal begins.",
            lambda rules: rules.goals.learning_count,
            lambda rules: rules.goals.learning_step,
            lambda rules: rules.goals.learning_points,
            metrics=(M.KNOWLEDGE, M.THEORIES),
            basis=GoalBasis.GAINED,
        ),
        ScenarioSpec(
            S.TEEMING_LIFE,
            C.LIFE,
            lambda target: "Teeming life",
            lambda rules, target: f"{several(target, 'new species appears', 'new species appear')} after the goal begins.",
            lambda rules: rules.goals.teeming_species,
            lambda rules: rules.goals.teeming_step,
            lambda rules: rules.goals.teeming_points,
            metrics=(M.SPECIES,),
            basis=GoalBasis.GAINED,
        ),
        ScenarioSpec(
            S.CREATORS_FAITHFUL,
            C.FAITH,
            lambda target: "The Creator's faithful",
            lambda rules, target: f"{several(target, 'community worships', 'communities worship')} you directly.",
            lambda rules: rules.goals.faithful_communities,
            lambda rules: rules.goals.faithful_step,
            lambda rules: rules.goals.faithful_points,
            metrics=(M.CREATOR_WORSHIPPERS,),
        ),
        ScenarioSpec(
            S.CUSTOM,
            C.CREATOR,
            lambda target: "A goal of your own",
            lambda rules, target: "Choose any measure of the cosmos, a target, a hold and a deadline.",
            lambda rules: 1,
            lambda rules: 0,
            lambda rules: rules.goals.custom_points,
        ),
    )
}


SCENARIO_STATUS_LABELS: dict[ScenarioStatus, str] = {
    ScenarioStatus.RUNNING: "Running",
    ScenarioStatus.COMPLETED: "Completed",
    ScenarioStatus.FAILED: "Failed",
    ScenarioStatus.ABANDONED: "Abandoned",
}
