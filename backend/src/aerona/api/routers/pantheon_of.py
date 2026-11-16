from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import or_, select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.pantheon_of import PantheonOfView, PantheonStructureView, PantheonTieView, SyncretismView
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.pantheon import PantheonStructureRow, PantheonTieRow, SyncretismRow
from aerona.db.tables.sons import SonRow

router = APIRouter(tags=["pantheon"])
NodeId = Annotated[int, Path(ge=1)]


@router.get("/pantheon/of/{node_id}", response_model=PantheonOfView)
async def pantheon_of(services: ServicesDep, node_id: NodeId) -> PantheonOfView:
    async with reader(services) as session:
        if await session.get(NodeRow, node_id) is None:
            raise NotFoundError("No such thing.")
        foreign = await session.get(ForeignGodRow, node_id)
        son = await session.get(SonRow, node_id)
        entity = await session.get(EntityRow, node_id)
        world_id = node_id if await session.get(WorldRow, node_id) is not None else foreign.world_id if foreign is not None else None
        if world_id is None and entity is not None:
            world_id = entity.world_id
        structure = await session.get(PantheonStructureRow, world_id) if world_id is not None else None
        ties = list(
            await session.scalars(
                select(PantheonTieRow)
                .where(or_(PantheonTieRow.god_node_id == node_id, PantheonTieRow.other_node_id == node_id))
                .order_by(PantheonTieRow.god_node_id)
            )
        )
        joined = or_(SyncretismRow.foreign_god_id == node_id, SyncretismRow.son_id == node_id, SyncretismRow.people_entity_id == node_id)
        syncretisms = list(await session.scalars(select(SyncretismRow).where(joined).order_by(SyncretismRow.id)))
        ids = {node_id}
        if structure is not None:
            ids |= {structure.world_id} | ({structure.head_node_id} if structure.head_node_id is not None else set())
        for tie in ties:
            ids |= {tie.god_node_id, tie.other_node_id}
        for row in syncretisms:
            ids |= {row.foreign_god_id, row.son_id, row.people_entity_id} | ({row.dominant_node_id} if row.dominant_node_id is not None else set())
        refs = await node_refs(session, sorted(ids))
        return PantheonOfView(
            node=refs[node_id],
            is_god=foreign is not None or son is not None,
            pantheon=PantheonStructureView(
                world=refs[structure.world_id],
                structure=structure.structure,
                head=refs.get(structure.head_node_id) if structure.head_node_id is not None else None,
                since_epoch=structure.since_epoch,
                locked=list(structure.locked),
            )
            if structure is not None
            else None,
            ties=[
                PantheonTieView(god=refs[tie.god_node_id], other=refs[tie.other_node_id], tie=tie.tie, since_epoch=tie.since_epoch, locked=list(tie.locked))
                for tie in ties
            ],
            syncretisms=[
                SyncretismView(
                    id=row.id,
                    foreign_god=refs[row.foreign_god_id],
                    son=refs[row.son_id],
                    people=refs[row.people_entity_id],
                    dominant=refs.get(row.dominant_node_id) if row.dominant_node_id is not None else None,
                    since_epoch=row.since_epoch,
                    locked=list(row.locked),
                )
                for row in syncretisms
            ],
        )
