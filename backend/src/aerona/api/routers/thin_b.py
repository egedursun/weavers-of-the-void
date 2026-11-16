from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.thin_b import RiftControlsView, RiftControlView, SourceTrustOfView, SourceTrustView
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.belief_depth import SourceTrustRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.rift_control import RiftControlRow

router = APIRouter(tags=["beliefs"])
NodeId = Annotated[int, Path(ge=1)]


@router.get("/beliefs/trust/of/{node_id}", response_model=SourceTrustOfView)
async def trust_of(services: ServicesDep, node_id: NodeId) -> SourceTrustOfView:
    async with reader(services) as session:
        if await session.get(NodeRow, node_id) is None:
            raise NotFoundError("No such thing.")
        refs = await node_refs(session, [node_id])
        rows = list(await session.scalars(select(SourceTrustRow).where(SourceTrustRow.holder_node_id == node_id).order_by(SourceTrustRow.source)))
        return SourceTrustOfView(
            node=refs[node_id],
            sources=[
                SourceTrustView(source=row.source, trust=row.trust, right=row.right, wrong=row.wrong, updated_epoch=row.updated_epoch, locked=list(row.locked))
                for row in rows
            ],
        )


@router.get("/rifts/controls", response_model=RiftControlsView)
async def rift_controls(services: ServicesDep) -> RiftControlsView:
    async with reader(services) as session:
        rows = list(await session.scalars(select(RiftControlRow).order_by(RiftControlRow.rift_id)))
        refs = await node_refs(session, [row.claimant_entity_id for row in rows if row.claimant_entity_id is not None])
        return RiftControlsView(
            controls=[
                RiftControlView(
                    rift_id=row.rift_id,
                    claimant=refs.get(row.claimant_entity_id) if row.claimant_entity_id is not None else None,
                    work=row.work,
                    toll=row.toll,
                    adapted=row.adapted,
                    claimed_epoch=row.claimed_epoch,
                    locked=list(row.locked),
                )
                for row in rows
            ]
        )
