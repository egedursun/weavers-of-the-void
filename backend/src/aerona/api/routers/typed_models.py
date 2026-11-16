from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import or_, select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.typed_models import AspectView, CreatureAttackRecord, HeroQuestView, HorrorEventView, TypedModelsView
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.anatomy import CreatureAttackRow
from aerona.db.tables.cosmography import DimensionRow
from aerona.db.tables.dimension_aspects import DimensionAspectRow
from aerona.db.tables.horror import HorrorEventRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.warfare import HeroQuestRow

router = APIRouter(tags=["typed-models"])
NodeId = Annotated[int, Path(ge=1)]


@router.get("/typed/of/{node_id}", response_model=TypedModelsView)
async def typed_of(services: ServicesDep, node_id: NodeId) -> TypedModelsView:
    async with reader(services) as session:
        if await session.get(NodeRow, node_id) is None:
            raise NotFoundError("No such thing.")
        touched = or_(HorrorEventRow.world_id == node_id, HorrorEventRow.subject_node_id == node_id, HorrorEventRow.source_node_id == node_id)
        horrors = list(await session.scalars(select(HorrorEventRow).where(touched).order_by(HorrorEventRow.id.desc())))
        attacks = list(await session.scalars(select(CreatureAttackRow).where(CreatureAttackRow.node_id == node_id).order_by(CreatureAttackRow.id)))
        quests = list(await session.scalars(select(HeroQuestRow).where(HeroQuestRow.hero_entity_id == node_id).order_by(HeroQuestRow.id.desc())))
        aspects = list(await session.scalars(select(DimensionAspectRow).where(DimensionAspectRow.dimension_id == node_id).order_by(DimensionAspectRow.id)))
        ids = {node_id}
        for row in horrors:
            ids |= {row.world_id} | {item for item in (row.source_node_id, row.subject_node_id) if item is not None}
        ids |= {row.target_node_id for row in quests if row.target_node_id is not None}
        refs = await node_refs(session, sorted(ids))
        return TypedModelsView(
            node=refs[node_id],
            is_dimension=await session.get(DimensionRow, node_id) is not None,
            horrors=[
                HorrorEventView(
                    id=row.id,
                    world=refs[row.world_id],
                    name=row.name,
                    target=row.target,
                    effect=row.effect,
                    scope=row.scope,
                    sense=row.sense,
                    source=row.source,
                    source_node=refs.get(row.source_node_id) if row.source_node_id is not None else None,
                    subject=refs.get(row.subject_node_id) if row.subject_node_id is not None else None,
                    duration=row.duration,
                    sanity_cost=row.sanity_cost,
                    leak=row.leak,
                    epoch=row.epoch,
                    until_epoch=row.until_epoch,
                    locked=list(row.locked),
                )
                for row in horrors
            ],
            attacks=[CreatureAttackRecord.model_validate(row) for row in attacks],
            quests=[
                HeroQuestView(
                    id=row.id,
                    aim=row.aim,
                    target_kind=row.target_kind,
                    obstacle=row.obstacle,
                    reward=row.reward,
                    scale=row.scale,
                    target=refs.get(row.target_node_id) if row.target_node_id is not None else None,
                    description=row.description,
                    status=row.status,
                    started_epoch=row.started_epoch,
                    ended_epoch=row.ended_epoch,
                    locked=list(row.locked),
                )
                for row in quests
            ],
            aspects=[AspectView.model_validate(row) for row in aspects],
        )
