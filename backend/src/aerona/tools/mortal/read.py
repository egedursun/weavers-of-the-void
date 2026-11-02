from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import QUERY_MAX
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.bond import BondKind
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import CommonResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import EmptyInput, ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, no_cost
from aerona.tools.framework.validation import fail
from aerona.tools.framework.views import entity_detail, entity_lines, search

READ = ToolMeta(ActionKind.OTHER, no_cost, read_only=True)
SEARCH_WIDENING = 4


class InspectInput(ToolInput):
    id: int


class SearchInput(ToolInput):
    query: Annotated[str, Field(max_length=QUERY_MAX)] = ""


async def horizon(call: MortalCall) -> set[int]:
    atlas = await call.atlas()
    region = atlas.top_region(call.me.id)
    if region is None:
        return set()
    return {region, *atlas.neighbour_regions(region)}


async def bonded(call: MortalCall, entity: EntityRow) -> bool:
    return bool(await BondRepository(call.session).active_between(call.me.id, entity.id, list(BondKind)))


async def knowable(call: MortalCall, entity: EntityRow, regions: set[int]) -> bool:
    if entity.id == call.me.id:
        return True
    if entity.world_id == call.me.world_id:
        region = (await call.atlas()).top_region(entity.id)
        if region is None or region in regions:
            return True
    return await bonded(call, entity)


async def look_at_world(call: MortalCall, _args: EmptyInput) -> str:
    views = call.ports.views
    if views is None:
        fail(CommonResult.NOT_AVAILABLE, tool=MortalToolId.LOOK_AT_WORLD.value)
    return await views.mortal_view(call.session, call.rules, call.me)


async def inspect_entity(call: MortalCall, args: InspectInput) -> str:
    entity = await call.session.get(EntityRow, args.id)
    if entity is None:
        fail(CommonResult.NO_SUCH_ENTITY, id=args.id)
    if not await knowable(call, entity, await horizon(call)):
        fail(CommonResult.NOT_IN_REACH, id=entity.id, name=entity.name)
    return await entity_detail(call.session, call.rules, entity)


async def search_entities(call: MortalCall, args: SearchInput) -> str:
    limit = call.rules.context.search_results_max
    candidates = await search(call.session, args.query, entity_type=None, limit=limit * SEARCH_WIDENING, world_ids=[call.me.world_id])
    regions = await horizon(call)
    found = [entity for entity in candidates if await knowable(call, entity, regions)][:limit]
    return await entity_lines(call.session, found) if found else result(CommonResult.NO_RESULTS)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    return [
        ToolSpec(MortalToolId.LOOK_AT_WORLD, mortal, EmptyInput, READ, look_at_world, frozenset({"views"})),
        ToolSpec(MortalToolId.INSPECT_ENTITY, mortal, InspectInput, READ, inspect_entity),
        ToolSpec(MortalToolId.SEARCH_ENTITIES, mortal, SearchInput, READ, search_entities),
    ]
