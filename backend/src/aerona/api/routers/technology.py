from typing import Annotated

from fastapi import APIRouter, Path

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.technology import TechLevelView, TechnologyNodeView
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.node import NodeRow
from aerona.db.tables.technology import TechnologyProfileRow
from aerona.domain.enums.eras import TechFamily
from aerona.engine.technology.profiles import family_level

router = APIRouter(tags=["technology"])
NodeId = Annotated[int, Path(ge=1)]


@router.get("/technology/of/{node_id}", response_model=TechnologyNodeView)
async def node_technology(services: ServicesDep, node_id: NodeId) -> TechnologyNodeView:
    async with reader(services) as session:
        if await session.get(NodeRow, node_id) is None:
            raise NotFoundError("No such thing.")
        refs = await node_refs(session, [node_id])
        families = []
        for family in TechFamily:
            row = await session.get(TechnologyProfileRow, (node_id, family))
            level = row.level if row is not None else await family_level(session, node_id, family)
            families.append(TechLevelView(family=family, level=level, own=row is not None, held=row is not None and "level" in row.locked))
        return TechnologyNodeView(node=refs[node_id], families=families)
