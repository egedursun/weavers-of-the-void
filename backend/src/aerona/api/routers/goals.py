from fastapi import APIRouter, Query

from aerona.api.actions import Alias, mount_all
from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.domain.enums.meta import GoalBasis, GoalComparator, GoalMetric, ScenarioKey
from aerona.services.gods.goals import GoalQuote, GoalsOverview, goals_overview, quote_goal
from aerona.services.gods.opportunities import PlayerHints, player_hints

router = APIRouter(tags=["goals"])

ALIASES = (
    Alias("POST", "/scenarios", "scenario:start"),
    Alias("POST", "/scenarios/custom", "scenario:custom"),
    Alias("POST", "/scenarios/{scenario_id}/edit", "scenario:edit", path_fields={"scenario_id": "scenario_id"}),
    Alias("POST", "/scenarios/{scenario_id}/hold", "scenario:hold", path_fields={"scenario_id": "scenario_id"}),
    Alias("POST", "/scenarios/{scenario_id}/abandon", "scenario:abandon", path_fields={"scenario_id": "scenario_id"}),
    Alias("POST", "/scenarios/{scenario_id}/delete", "scenario:delete", path_fields={"scenario_id": "scenario_id"}),
)


@router.get("/goals", response_model=GoalsOverview)
async def goals(services: ServicesDep) -> GoalsOverview:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        return await goals_overview(session, rules)


@router.get("/goals/quote", response_model=GoalQuote)
async def goal_quote(
    services: ServicesDep,
    *,
    key: ScenarioKey = ScenarioKey.DOOM_FAR,
    target: int | None = Query(None, ge=0),
    deadline_epochs: int | None = Query(None, ge=1),
    metric: GoalMetric | None = None,
    comparator: GoalComparator = GoalComparator.AT_LEAST,
    basis: GoalBasis = GoalBasis.TOTAL,
    hold_epochs: int = Query(0, ge=0),
) -> GoalQuote:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        return await quote_goal(
            session, rules, key, target=target, deadline_epochs=deadline_epochs, metric=metric, comparator=comparator, basis=basis, hold_epochs=hold_epochs
        )


@router.get("/opportunities", response_model=PlayerHints)
async def opportunities(services: ServicesDep) -> PlayerHints:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        return await player_hints(session, rules)


mount_all(router, ALIASES, tag="goals")
