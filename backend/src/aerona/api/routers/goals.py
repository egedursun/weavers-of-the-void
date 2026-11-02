from fastapi import APIRouter

from aerona.api.actions import Alias, mount_all
from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.services.gods.goals import GoalsOverview, goals_overview
from aerona.services.gods.opportunities import PlayerHints, player_hints

router = APIRouter(tags=["goals"])

ALIASES = (
    Alias("POST", "/scenarios", "scenario:start"),
    Alias("POST", "/scenarios/{scenario_id}/abandon", "scenario:abandon", path_fields={"scenario_id": "scenario_id"}),
)


@router.get("/goals", response_model=GoalsOverview)
async def goals(services: ServicesDep) -> GoalsOverview:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        return await goals_overview(session, rules)


@router.get("/opportunities", response_model=PlayerHints)
async def opportunities(services: ServicesDep) -> PlayerHints:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        return await player_hints(session, rules)


mount_all(router, ALIASES, tag="goals")
