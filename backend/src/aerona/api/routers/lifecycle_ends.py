from typing import Annotated

from fastapi import APIRouter, Path

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.lifecycle_ends import LifecycleNodeView
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lifecycle_ends import LifecycleStateRow
from aerona.domain.enums.lifecycle_end import LifecycleKind
from aerona.engine.lifecycle.ends import KIND_OF_TYPE, LIVING

router = APIRouter(tags=["lifecycle"])
NodeId = Annotated[int, Path(ge=1)]
NO_LIFE = "Only an ideology, a theory, a rite, a disease or an outer being can fall dormant, be lost, die out or be banished; this thing has no such life."


@router.get("/lifecycle/of/{node_id}", response_model=LifecycleNodeView)
async def node_lifecycle(services: ServicesDep, node_id: NodeId) -> LifecycleNodeView:
    async with reader(services) as session:
        own = await node_refs(session, [node_id])
        if node_id not in own:
            raise NotFoundError("No such thing.")
        rules = await world_rules(services, session)
        table = rules.lifecycle_ends
        entity = await session.get(EntityRow, node_id)
        kind = KIND_OF_TYPE.get(entity.entity_type) if entity is not None else None
        if entity is None or kind is None:
            return LifecycleNodeView(
                node=own[node_id],
                kind=None,
                state=None,
                cause=None,
                idle_epochs=0,
                grace_epochs=0,
                since_epoch=None,
                holders=0,
                texts=0,
                seeded=False,
                locked=[],
                destroy_cost=table.destroy_cost,
                absent_reason=NO_LIFE,
            )
        row = await session.get(LifecycleStateRow, node_id)
        epoch = row.updated_epoch if row is not None else 0
        living = await LIVING[kind](session, node_id, epoch, table.practice_epochs)
        grace = {LifecycleKind.DISEASE: table.eradication_epochs, LifecycleKind.RITE: table.practice_epochs}.get(kind, 1)
        return LifecycleNodeView(
            node=own[node_id],
            kind=kind,
            state=row.state if row is not None else None,
            cause=row.cause if row is not None else None,
            idle_epochs=row.idle_epochs if row is not None else 0,
            grace_epochs=grace,
            since_epoch=row.since_epoch if row is not None else None,
            holders=living.holders,
            texts=living.texts,
            seeded=row is not None,
            locked=list(row.locked) if row is not None else [],
            destroy_cost=table.destroy_cost,
            absent_reason=None,
        )
