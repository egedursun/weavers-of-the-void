from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.world_views import WorldNatureView, WorldViewNodeView
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.world_views import WorldViewRow
from aerona.engine.cosmos.world_views import WorldView, default_view, view_from

router = APIRouter(tags=["world-views"])
NodeId = Annotated[int, Path(ge=1)]
NO_WORLD = "It stands on no world: the Creator, stars and things between worlds carry no world's nature."


async def world_of(session: AsyncSession, node_id: int) -> WorldRow | None:
    world = await session.get(WorldRow, node_id)
    if world is not None:
        return world
    entity = await session.get(EntityRow, node_id)
    son = await session.get(SonRow, node_id) if entity is None else None
    god = await session.get(ForeignGodRow, node_id) if entity is None and son is None else None
    world_id = entity.world_id if entity is not None else son.current_world_id if son is not None else god.world_id if god is not None else None
    return await session.get(WorldRow, world_id) if world_id is not None else None


def nature(view: WorldView) -> WorldNatureView:
    return WorldNatureView(**asdict(view))


@router.get("/world-views/of/{node_id}", response_model=WorldViewNodeView)
async def node_world_view(services: ServicesDep, node_id: NodeId) -> WorldViewNodeView:
    async with reader(services) as session:
        own = await node_refs(session, [node_id])
        if node_id not in own:
            raise NotFoundError("No such thing.")
        rules = await world_rules(services, session)
        world = await world_of(session, node_id)
        if world is None:
            return WorldViewNodeView(
                node=own[node_id],
                world=None,
                world_type=None,
                nature=None,
                kind_nature=None,
                seeded=False,
                updated_epoch=None,
                locked=[],
                absent_reason=NO_WORLD,
            )
        refs = await node_refs(session, [world.id])
        row = await session.get(WorldViewRow, world.id)
        kind = default_view(rules, world.world_type)
        return WorldViewNodeView(
            node=own[node_id],
            world=refs.get(world.id),
            world_type=world.world_type,
            nature=nature(view_from(row) if row is not None else kind),
            kind_nature=nature(kind),
            seeded=row is not None,
            updated_epoch=row.updated_epoch if row is not None else None,
            locked=list(row.locked) if row is not None else [],
            absent_reason=None,
        )
