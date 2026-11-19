from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import func, select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.routers.world_views import world_of
from aerona.api.schemas.fossils import FossilBedView, FossilNodeView
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.fossils import FossilBedRow
from aerona.domain.enums.entity import EntityType
from aerona.engine.primitives.distance import RegionAtlas

router = APIRouter(tags=["fossils"])
NodeId = Annotated[int, Path(ge=1)]
NO_LAND = "It stands in no land: the Creator, stars and things between worlds hold no fossil beds."


@router.get("/fossils/of/{node_id}", response_model=FossilNodeView)
async def node_fossils(services: ServicesDep, node_id: NodeId) -> FossilNodeView:
    async with reader(services) as session:
        own = await node_refs(session, [node_id])
        if node_id not in own:
            raise NotFoundError("No such thing.")
        entity = await session.get(EntityRow, node_id)
        region_id = node_id if entity is not None and entity.entity_type is EntityType.REGION else (await RegionAtlas.load(session)).top_region(node_id)
        world = await world_of(session, node_id)
        world_id = world.id if world is not None else None
        scope = FossilBedRow.region_entity_id == region_id if region_id is not None else FossilBedRow.world_id == world_id
        rows = list(await session.scalars(select(FossilBedRow).where(scope).order_by(FossilBedRow.id))) if region_id or world_id else []
        ids = {item for row in rows for item in (row.region_entity_id, row.source_entity_id, row.disease_entity_id, row.finder_entity_id) if item}
        refs = await node_refs(session, sorted(ids | ({region_id} if region_id else set())))
        counted = select(func.count()).select_from(FossilBedRow).where(FossilBedRow.world_id == world_id)
        found = await session.scalar(counted.where(FossilBedRow.found_epoch.is_not(None)))
        hidden = await session.scalar(counted.where(FossilBedRow.found_epoch.is_(None)))
        return FossilNodeView(
            node=own[node_id],
            region=refs.get(region_id) if region_id else None,
            beds=[
                FossilBedView(
                    id=row.id,
                    region=refs.get(row.region_entity_id),
                    source=row.source,
                    source_node=refs.get(row.source_entity_id) if row.source_entity_id else None,
                    richness=row.richness,
                    frozen=row.frozen,
                    disease=refs.get(row.disease_entity_id) if row.disease_entity_id else None,
                    laid_epoch=row.laid_epoch,
                    found_epoch=row.found_epoch,
                    finder=refs.get(row.finder_entity_id) if row.finder_entity_id else None,
                    reading=row.reading,
                    layer=row.layer,
                    preservation=row.preservation,
                    locked=list(row.locked),
                )
                for row in rows
            ],
            world_found=int(found or 0),
            world_hidden=int(hidden or 0),
            absent_reason=NO_LAND if region_id is None and world_id is None else None,
        )
