from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import or_, select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.fortune import CohortMishapView, FortuneMishapView, FortuneNodeView, FortuneSourceView
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folkways import MishapRow
from aerona.db.tables.fortune import CohortMishapRateRow, FortuneLawRow, FortuneProfileRow, FortuneSourceRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.fortune import FortuneLaw

router = APIRouter(tags=["fortune"])
NodeId = Annotated[int, Path(ge=1)]


@router.get("/fortune/of/{node_id}", response_model=FortuneNodeView)
async def node_fortune(services: ServicesDep, node_id: NodeId) -> FortuneNodeView:
    async with reader(services) as session:
        if await session.get(NodeRow, node_id) is None:
            raise NotFoundError("No such thing.")
        profile = await session.get(FortuneProfileRow, node_id)
        entity = await session.get(EntityRow, node_id)
        world_id = entity.world_id if entity is not None else node_id if await session.get(WorldRow, node_id) is not None else None
        law = await session.get(FortuneLawRow, world_id) if world_id is not None else None
        sources = list(await session.scalars(select(FortuneSourceRow).where(FortuneSourceRow.holder_node_id == node_id).order_by(FortuneSourceRow.id.desc())))
        mishaps = list(
            await session.scalars(
                select(MishapRow).where(or_(MishapRow.victim_node_id == node_id, MishapRow.settlement_entity_id == node_id)).order_by(MishapRow.id.desc())
            )
        )
        cohort = list(
            await session.scalars(
                select(CohortMishapRateRow).where(CohortMishapRateRow.community_entity_id == node_id).order_by(CohortMishapRateRow.epoch.desc())
            )
        )
        refs = await node_refs(session, [node_id, *(row.giver_node_id for row in sources if row.giver_node_id is not None)])
        return FortuneNodeView(
            node=refs[node_id],
            fortune=profile.fortune if profile is not None else 0,
            streak=profile.streak if profile is not None else 0,
            held_values=list(profile.locked) if profile is not None else [],
            law=law.law if law is not None else FortuneLaw.PERSONAL,
            world_id=world_id,
            sources=[
                FortuneSourceView(
                    id=row.id,
                    kind=row.kind,
                    strength=row.strength,
                    giver=refs.get(row.giver_node_id) if row.giver_node_id is not None else None,
                    until_epoch=row.until_epoch,
                    since_epoch=row.since_epoch,
                    locked=list(row.locked),
                )
                for row in sources
            ],
            mishaps=[
                FortuneMishapView(id=row.id, kind=row.kind, severity=row.severity, died=row.died, explained=row.explained, epoch=row.epoch) for row in mishaps
            ],
            cohort=[CohortMishapView(epoch=row.epoch, injured=row.injured, dead=row.dead, rate_pct=row.rate_pct) for row in cohort],
        )
