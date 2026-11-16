from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.creator_bonds import ChosenView, CovenantView, CreatorBondsView, CreatorStandingView, DepictionView
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.creator_bonds import CovenantRow, CreatorChosenRow, CreatorDepictionRow, CreatorStandingRow
from aerona.db.tables.divine import WorldAttentionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.entity import EntityType

router = APIRouter(tags=["creator"])
NodeId = Annotated[int, Path(ge=1)]


def depicted(row: CreatorDepictionRow | None) -> DepictionView | None:
    if row is None:
        return None
    return DepictionView(name=row.name, nature=row.nature, aspect=row.aspect, updated_epoch=row.updated_epoch, locked=list(row.locked))


@router.get("/creator/bonds/of/{node_id}", response_model=CreatorBondsView)
async def node_bonds(services: ServicesDep, node_id: NodeId) -> CreatorBondsView:
    async with reader(services) as session:
        if await session.get(NodeRow, node_id) is None:
            raise NotFoundError("No such thing.")
        refs = await node_refs(session, [node_id])
        entity = await session.get(EntityRow, node_id)
        is_people = entity is not None and entity.entity_type is EntityType.PEOPLE
        standing = await session.get(CreatorStandingRow, node_id)
        depiction = await session.get(CreatorDepictionRow, node_id)
        chosen = await session.get(CreatorChosenRow, node_id)
        attention = await session.get(WorldAttentionRow, node_id)
        covenants = list(await session.scalars(select(CovenantRow).where(CovenantRow.people_entity_id == node_id).order_by(CovenantRow.id)))
        return CreatorBondsView(
            node=refs[node_id],
            is_people=is_people,
            standing=CreatorStandingView(
                awe=standing.awe,
                love=standing.love,
                dread=standing.dread,
                gratitude=standing.gratitude,
                resentment=standing.resentment,
                ignorance=standing.ignorance,
                stance=standing.stance,
                heresy=standing.heresy,
                updated_epoch=standing.updated_epoch,
                locked=list(standing.locked),
            )
            if standing is not None
            else None,
            depiction=depicted(depiction),
            covenants=[
                CovenantView(
                    id=row.id,
                    duty=row.duty,
                    promise=row.promise,
                    seal_sign=row.seal_sign,
                    state=row.state,
                    since_epoch=row.since_epoch,
                    until_epoch=row.until_epoch,
                    breaches=row.breaches,
                    locked=list(row.locked),
                )
                for row in covenants
            ],
            chosen=ChosenView(favour=chosen.favour, since_epoch=chosen.since_epoch, locked=list(chosen.locked)) if chosen is not None else None,
            far_epochs=attention.far_epochs if attention is not None else None,
        )
