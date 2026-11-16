from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.divine_powers import DivinePowersNodeView, DivinePowerView
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.divine_powers import DivinePowerRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.domain import Domain

router = APIRouter(tags=["divine"])
NodeId = Annotated[int, Path(ge=1)]


@router.get("/divine/powers/of/{node_id}", response_model=DivinePowersNodeView)
async def node_powers(services: ServicesDep, node_id: NodeId) -> DivinePowersNodeView:
    async with reader(services) as session:
        if await session.get(NodeRow, node_id) is None:
            raise NotFoundError("No such thing.")
        cosmos = await CosmosRepository(session).get()
        epoch = cosmos.epoch if cosmos is not None else 0
        refs = await node_refs(session, [node_id])
        rows = list(await session.scalars(select(DivinePowerRow).where(DivinePowerRow.holder_node_id == node_id).order_by(DivinePowerRow.id)))
        powers = [
            DivinePowerView(
                id=row.id,
                name=row.name,
                verb=row.verb,
                object=row.object,
                object_key=row.object_key,
                scope=row.scope,
                mode=row.mode,
                cost=row.cost,
                cost_amount=row.cost_amount,
                cooldown=row.cooldown,
                strength=row.strength,
                domains=[Domain(item) for item in row.domains if item in Domain._value2member_map_],
                son_preset=row.son_preset,
                foreign_preset=row.foreign_preset,
                last_used_epoch=row.last_used_epoch,
                granted_epoch=row.granted_epoch,
                ready=row.last_used_epoch is None or epoch - row.last_used_epoch >= row.cooldown,
                locked=list(row.locked),
            )
            for row in rows
        ]
        return DivinePowersNodeView(node=refs[node_id], powers=powers)
