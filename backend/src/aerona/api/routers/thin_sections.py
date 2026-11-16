from typing import Annotated

from fastapi import APIRouter, Path, Query
from sqlalchemy import or_, select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.thin_sections import ConstitutionOfView, ConstitutionView, JourneyEncounterView, RelationPartsView, RelationPartView
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.node import NodeRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.thin_sections import ConstitutionRow, JourneyEncounterRow, RelationComponentRow
from aerona.engine.services.community_relations import pair_key

router = APIRouter(tags=["thin_sections"])
NodeId = Annotated[int, Path(ge=1)]


@router.get("/relations/{first_id}/{second_id}/parts", response_model=RelationPartsView)
async def relation_parts(services: ServicesDep, first_id: NodeId, second_id: NodeId) -> RelationPartsView:
    async with reader(services) as session:
        refs = await node_refs(session, [first_id, second_id])
        if first_id not in refs or second_id not in refs:
            raise NotFoundError("Both ends of a relation must exist.")
        low, high = pair_key(first_id, second_id)
        rows = await session.scalars(
            select(RelationComponentRow)
            .where(RelationComponentRow.entity_a_id == low, RelationComponentRow.entity_b_id == high)
            .order_by(RelationComponentRow.component)
        )
        parts = [RelationPartView(component=row.component, value=row.value, updated_epoch=row.updated_epoch, locked=list(row.locked)) for row in rows]
        return RelationPartsView(parts=parts)


@router.get("/constitutions/of/{node_id}", response_model=ConstitutionOfView)
async def constitution_of(services: ServicesDep, node_id: NodeId) -> ConstitutionOfView:
    async with reader(services) as session:
        if await session.get(NodeRow, node_id) is None:
            raise NotFoundError("No such thing.")
        realm = await session.get(PolityProfileRow, node_id)
        row = await session.get(ConstitutionRow, node_id)
        refs = await node_refs(session, [node_id, *([row.ideology_entity_id] if row is not None and row.ideology_entity_id is not None else [])])
        view = (
            ConstitutionView(
                ideology=refs.get(row.ideology_entity_id) if row.ideology_entity_id is not None else None,
                selectorate=row.selectorate,
                offices=row.offices,
                rights=row.rights,
                written_epoch=row.written_epoch,
                locked=list(row.locked),
            )
            if row is not None
            else None
        )
        return ConstitutionOfView(is_realm=realm is not None, constitution=view)


@router.get("/journey-encounters", response_model=list[JourneyEncounterView])
async def journey_encounters(services: ServicesDep, world_id: Annotated[int | None, Query(ge=1)] = None) -> list[JourneyEncounterView]:
    async with reader(services) as session:
        query = select(JourneyEncounterRow)
        if world_id is not None:
            query = query.where(or_(JourneyEncounterRow.world_id.is_(None), JourneyEncounterRow.world_id == world_id))
        rows = list(await session.scalars(query.order_by(JourneyEncounterRow.environment, JourneyEncounterRow.effect, JourneyEncounterRow.id)))
        refs = await node_refs(session, sorted({row.world_id for row in rows if row.world_id is not None}))
        return [
            JourneyEncounterView(
                id=row.id,
                world=refs.get(row.world_id) if row.world_id is not None else None,
                environment=row.environment,
                effect=row.effect,
                name=row.name,
                weight=row.weight,
                loss_pct=row.loss_pct,
                locked=list(row.locked),
            )
            for row in rows
        ]
