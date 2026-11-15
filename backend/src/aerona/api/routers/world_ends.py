from typing import Annotated

from fastapi import APIRouter, Path

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.routers.world_views import NO_WORLD, world_of
from aerona.api.schemas.world_ends import WorldEndNodeView
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.world_ends import WorldEndRow

router = APIRouter(tags=["world-ends"])
NodeId = Annotated[int, Path(ge=1)]


@router.get("/world-ends/of/{node_id}", response_model=WorldEndNodeView)
async def node_world_end(services: ServicesDep, node_id: NodeId) -> WorldEndNodeView:
    async with reader(services) as session:
        own = await node_refs(session, [node_id])
        if node_id not in own:
            raise NotFoundError("No such thing.")
        rules = await world_rules(services, session)
        world = await world_of(session, node_id)
        row = await session.get(WorldEndRow, world.id) if world is not None else None
        refs = await node_refs(session, [world.id]) if world is not None else {}
        return WorldEndNodeView(
            node=own[node_id],
            world=refs.get(world.id) if world is not None else None,
            world_type=world.world_type if world is not None else None,
            state=row.state if row is not None else None,
            cause=row.cause if row is not None else None,
            epoch=row.epoch if row is not None else None,
            former_type=row.former_type if row is not None else None,
            new_type=row.new_type if row is not None else None,
            lives_ended=row.lives_ended if row is not None else 0,
            homeless=row.homeless if row is not None else 0,
            anchors_lost=row.anchors_lost if row is not None else 0,
            routes_closed=row.routes_closed if row is not None else 0,
            locked=list(row.locked) if row is not None else [],
            end_cost=rules.world_ends.end_cost,
            absent_reason=NO_WORLD if world is None else None,
        )
