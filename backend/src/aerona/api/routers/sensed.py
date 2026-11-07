from fastapi import APIRouter
from sqlalchemy import select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.db.tables.epochs import DeferredStepRow
from aerona.db.tables.routes import HorizonIntuitionRow
from aerona.domain.enums.epoch import DeferredStepKind, DeferredStepStatus
from aerona.domain.enums.travel import HorizonStatus

router = APIRouter(tags=["sensed"])


class SensedStepView(ApiModel):
    id: int
    intuition_id: int | None
    seeker: NodeRef | None
    status: DeferredStepStatus
    attempts: int
    error: str | None
    epoch: int
    result_world: int | None


class WaitingIntuitionView(ApiModel):
    id: int
    seeker: NodeRef | None
    epoch: int
    how: str | None
    queued: bool


class SensedWorldsView(ApiModel):
    steps: list[SensedStepView]
    intuitions: list[WaitingIntuitionView]


@router.get("/sensed-worlds", response_model=SensedWorldsView)
async def sensed_worlds(services: ServicesDep) -> SensedWorldsView:
    async with reader(services) as session:
        steps = list(
            await session.scalars(select(DeferredStepRow).where(DeferredStepRow.kind == DeferredStepKind.SENSED_WORLD).order_by(DeferredStepRow.id.desc()))
        )
        waiting = list(
            await session.scalars(select(HorizonIntuitionRow).where(HorizonIntuitionRow.status == HorizonStatus.PENDING).order_by(HorizonIntuitionRow.id))
        )
        refs = await node_refs(
            session, [*(step.requested_by_node_id for step in steps if step.requested_by_node_id), *(row.mortal_entity_id for row in waiting)]
        )
        queued = {step.payload.get("intuition_id") for step in steps if step.status is not DeferredStepStatus.DONE}
        return SensedWorldsView(
            steps=[
                SensedStepView(
                    id=step.id,
                    intuition_id=step.payload.get("intuition_id"),
                    seeker=refs.get(step.requested_by_node_id) if step.requested_by_node_id is not None else None,
                    status=step.status,
                    attempts=step.attempts,
                    error=step.error,
                    epoch=step.epoch,
                    result_world=step.result_world_id,
                )
                for step in steps
            ],
            intuitions=[
                WaitingIntuitionView(id=row.id, seeker=refs.get(row.mortal_entity_id), epoch=row.epoch, how=row.how, queued=row.id in queued) for row in waiting
            ],
        )
