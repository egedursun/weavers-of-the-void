from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.prehistory_lines import happening_text
from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.routers.world_views import NO_WORLD, world_of
from aerona.api.schemas.prehistory import DeepTimeHappeningView, DeepTimeRunView, DeepTimeView, PrehistoryHappeningView, PrehistoryNodeView
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.prehistory import EPOCHS_MAX, RESOLUTION_MAX, DeepTimeEventRow, DeepTimeRunRow, PrehistoryEventRow, PrehistoryRow
from aerona.engine.cosmos.world_views import view_of
from aerona.engine.prehistory.digest import lore_free
from aerona.engine.primitives.manual import manual_context

router = APIRouter(tags=["prehistory"])
NodeId = Annotated[int, Path(ge=1)]


async def incident_text(session: AsyncSession, incident_id: int | None) -> str | None:
    incident = await session.get(IncidentRow, incident_id) if incident_id is not None else None
    line = await session.get(ChronicleRow, incident.chronicle_id) if incident is not None and incident.chronicle_id is not None else None
    return line.text if line is not None else None


@router.get("/prehistory/of/{node_id}", response_model=PrehistoryNodeView)
async def node_prehistory(services: ServicesDep, node_id: NodeId) -> PrehistoryNodeView:
    async with reader(services) as session:
        own = await node_refs(session, [node_id])
        if node_id not in own:
            raise NotFoundError("No such thing.")
        rules = await world_rules(services, session)
        world = await world_of(session, node_id)
        row = await session.get(PrehistoryRow, world.id) if world is not None else None
        events = (
            list(
                await session.scalars(
                    select(PrehistoryEventRow).where(PrehistoryEventRow.world_id == world.id).order_by(PrehistoryEventRow.round, PrehistoryEventRow.id)
                )
            )
            if world is not None
            else []
        )
        linked = [world.id] if world is not None else []
        linked += [row.source_world_id] if row is not None and row.source_world_id is not None else []
        linked += [event.subject_node_id for event in events if event.subject_node_id is not None]
        linked += [event.source_world_id for event in events if event.source_world_id is not None]
        refs = await node_refs(session, linked)
        free = await lore_free(await manual_context(session, "prehistory_view", rules), world.id) if world is not None else False
        view = await view_of(session, rules, world.id) if world is not None else None
        return PrehistoryNodeView(
            node=own[node_id],
            world=refs.get(world.id) if world is not None else None,
            world_type=world.world_type if world is not None else None,
            kind_of_world=view.prehistory_kind if view is not None else None,
            kind=row.kind if row is not None else None,
            state=row.state if row is not None else None,
            source=row.source if row is not None else None,
            epochs=row.epochs if row is not None else 0,
            resolution=row.resolution if row is not None else rules.prehistory.resolution,
            rounds_done=row.rounds_done if row is not None else 0,
            birth_epoch=row.birth_epoch if row is not None else None,
            seconds=row.seconds if row is not None else 0,
            slow_rounds=row.slow_rounds if row is not None else 0,
            source_world=refs.get(row.source_world_id) if row is not None and row.source_world_id is not None else None,
            locked=list(row.locked) if row is not None else [],
            happenings=[
                PrehistoryHappeningView(
                    id=event.id,
                    round=event.round,
                    magnitude=event.magnitude,
                    source=event.source,
                    text=await happening_text(session, event),
                    subject=refs.get(event.subject_node_id) if event.subject_node_id is not None else None,
                    source_world=refs.get(event.source_world_id) if event.source_world_id is not None else None,
                    mirrored=event.mirrored,
                    locked=list(event.locked),
                )
                for event in events
            ],
            lore_free=free,
            default_epochs=rules.prehistory.epochs,
            default_resolution=rules.prehistory.resolution,
            epochs_max=EPOCHS_MAX,
            resolution_max=RESOLUTION_MAX,
            seed_cost=rules.prehistory.seed_cost,
            absent_reason=NO_WORLD if world is None else None,
        )


@router.get("/deep-time", response_model=DeepTimeView)
async def deep_time(services: ServicesDep) -> DeepTimeView:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        runs = list(await session.scalars(select(DeepTimeRunRow).order_by(DeepTimeRunRow.id.desc())))
        views: list[DeepTimeRunView] = []
        for run in runs:
            events = await session.scalars(
                select(DeepTimeEventRow).where(DeepTimeEventRow.run_id == run.id).order_by(DeepTimeEventRow.epoch, DeepTimeEventRow.id)
            )
            views.append(
                DeepTimeRunView(
                    id=run.id,
                    epochs=run.epochs,
                    ran=run.ran,
                    from_epoch=run.from_epoch,
                    to_epoch=run.to_epoch,
                    state=run.state,
                    sons_simulated=run.sons_simulated,
                    locked=list(run.locked),
                    happenings=[
                        DeepTimeHappeningView(
                            id=event.id,
                            epoch=event.epoch,
                            magnitude=event.magnitude,
                            text=await incident_text(session, event.incident_id),
                            locked=list(event.locked),
                        )
                        for event in list(events)
                    ],
                )
            )
        return DeepTimeView(runs=views, max_epochs=rules.prehistory.deep_time_max_epochs, cost_per_epoch=rules.prehistory.deep_time_cost)
