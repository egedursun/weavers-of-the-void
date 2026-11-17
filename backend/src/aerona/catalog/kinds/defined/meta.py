from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.meta import GoalBasis, GoalComparator

GOAL_BASIS = total(
    GoalBasis,
    {
        GoalBasis.TOTAL: Defined(
            "Total",
            checked_by=(),
            used_by=(
                "api.routers.goals.goal_quote",
                "catalog.scenarios.ScenarioSpec",
                "engine.gods.goals.scenario_basis",
                "services.gods.goals.edit_scenario",
                "services.gods.goals.quote_goal",
                "services.player.goals.StartCustomGoal",
            ),
        ),
        GoalBasis.GAINED: Defined(
            "Gained",
            checked_by=(
                "catalog.scenarios.custom_description",
                "catalog.scenarios.custom_title",
                "engine.gods.goals.custom_points",
                "engine.gods.goals.goal_value",
                "engine.gods.goals.value_text",
                "services.gods.goals.checked_custom",
                "services.gods.goals.quote_goal",
            ),
            used_by=("catalog.scenarios.SCENARIOS",),
        ),
    },
)

GOAL_COMPARATOR = total(
    GoalComparator,
    {
        GoalComparator.AT_LEAST: Defined(
            "At least",
            checked_by=("catalog.scenarios.custom_description", "catalog.scenarios.custom_title"),
            used_by=(
                "api.routers.goals.goal_quote",
                "engine.gods.goals.scenario_comparator",
                "services.gods.goals.edit_scenario",
                "services.gods.goals.quote_goal",
                "services.player.goals.StartCustomGoal",
            ),
        ),
        GoalComparator.AT_MOST: Defined(
            "At most",
            checked_by=(
                "engine.gods.goals.custom_points",
                "engine.gods.goals.reached",
                "engine.gods.goals.toward",
                "engine.gods.goals.value_text",
                "services.gods.goals.checked_custom",
            ),
            used_by=(),
        ),
    },
)
