from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.routers.prehistory import incident_text
from aerona.api.schemas.transform import (
    KindChangeView,
    StarModifierView,
    TransformKindView,
    TransformNodeView,
    TransformProspectView,
    TransformTimelineView,
)
from aerona.api.views.common import node_refs
from aerona.catalog.transformations import END_OF_NODE, END_OF_TYPE, ENGINE_KINDS, TRANSFORMS
from aerona.core.errors import NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.transform import LUMINOSITY_SHIFT_MAX, StarModifierRow, TransformationRow, TransformProspectRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.transform import TransformEnd, TransformState

router = APIRouter(tags=["transformations"])
NodeId = Annotated[int, Path(ge=1)]


async def end_of(session: AsyncSession, node: NodeRow) -> TransformEnd | None:
    entity = await session.get(EntityRow, node.id)
    if entity is not None:
        return END_OF_TYPE.get(entity.entity_type)
    return END_OF_NODE.get(node.kind)


async def transformation_views(session: AsyncSession, rows: list[TransformationRow], epoch: int) -> list[KindChangeView]:
    refs = await node_refs(session, [node for row in rows for node in (row.subject_node_id, row.result_node_id) if node is not None])
    return [
        KindChangeView(
            id=row.id,
            kind=row.kind,
            epoch=row.epoch,
            trigger=row.trigger,
            state=row.state,
            subject=refs.get(row.subject_node_id) if row.subject_node_id is not None else None,
            result=refs.get(row.result_node_id) if row.result_node_id is not None else None,
            subject_name=row.subject_name,
            result_name=row.result_name,
            text=await incident_text(session, row.incident_id),
            revertible=row.state is TransformState.DONE and row.epoch == epoch and bool(row.undo),
            locked=row.locked,
        )
        for row in rows
    ]


def prospect_view(row: TransformProspectRow) -> TransformProspectView:
    return TransformProspectView(
        id=row.id,
        kind=row.kind,
        subject_id=row.subject_node_id,
        progress=row.progress,
        stance=row.stance,
        trigger=row.trigger,
        warned_epoch=row.warned_epoch,
        due_epoch=row.due_epoch,
        updated_epoch=row.updated_epoch,
        locked=row.locked,
    )


async def redemption_of(session: AsyncSession, son_id: int) -> tuple[list[int], list[int]]:
    worshipping = select(BondRow.source_node_id).where(BondRow.target_node_id == son_id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
    telling = select(BondRow.source_node_id).where(BondRow.target_node_id == son_id, BondRow.kind == BondKind.TELLS_OF, BondRow.state == BondState.ACTIVE)
    redeemers = await session.scalars(
        select(EntityRow.id)
        .where(
            EntityRow.status == EntityStatus.CANON,
            EntityRow.entity_type == EntityType.MORTAL,
            or_(EntityRow.id.in_(worshipping), EntityRow.affiliated_entity_id.in_(worshipping)),
        )
        .order_by(EntityRow.id)
    )
    legends = await session.scalars(
        select(EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON, EntityRow.entity_type == EntityType.LEGEND, EntityRow.id.in_(telling))
        .order_by(EntityRow.id)
    )
    return list(redeemers), list(legends)


@router.get("/transformations/of/{node_id}", response_model=TransformNodeView)
async def node_transformations(services: ServicesDep, node_id: NodeId) -> TransformNodeView:
    async with reader(services) as session:
        node = await session.get(NodeRow, node_id)
        if node is None:
            raise NotFoundError("No such thing.")
        rules = await world_rules(services, session)
        epoch = (await CosmosRepository(session).require_cosmos()).epoch
        came = list(await session.scalars(select(TransformationRow).where(TransformationRow.result_node_id == node.id).order_by(TransformationRow.id)))
        went = list(await session.scalars(select(TransformationRow).where(TransformationRow.subject_node_id == node.id).order_by(TransformationRow.id)))
        prospects = list(
            await session.scalars(select(TransformProspectRow).where(TransformProspectRow.subject_node_id == node.id).order_by(TransformProspectRow.kind))
        )
        modifiers = list(await session.scalars(select(StarModifierRow).where(StarModifierRow.star_id == node.id).order_by(StarModifierRow.id)))
        son = await session.get(SonRow, node.id)
        god = await session.get(ForeignGodRow, node.id)
        refs = await node_refs(
            session,
            [
                *[row.cause_node_id for row in modifiers if row.cause_node_id is not None],
                *([son.body_entity_id] if son is not None and son.body_entity_id is not None else []),
                *([god.anchor_world_id] if god is not None and god.anchor_world_id is not None else []),
                *([god.anchor_star_id] if god is not None and god.anchor_star_id is not None else []),
                node.id,
            ],
        )
        redeemer_ids, legend_ids = await redemption_of(session, son.id) if son is not None else ([], [])
        helpers = await node_refs(session, [*redeemer_ids, *legend_ids])
        end = await end_of(session, node)
        open_kinds = sorted(kind for kind, spec in TRANSFORMS.items() if end is not None and spec.source is end)
        return TransformNodeView(
            node=refs[node.id],
            end=end,
            epoch=epoch,
            warn_epochs=rules.transform.warn_epochs,
            came_from=await transformation_views(session, came, epoch),
            became=await transformation_views(session, went, epoch),
            prospects=[prospect_view(row) for row in prospects],
            open_kinds=open_kinds,
            forceable=[kind for kind in open_kinds if kind in ENGINE_KINDS],
            son_status=son.status if son is not None else None,
            sanity=son.sanity if son is not None else None,
            corruption_band=rules.transform.corruption_warning_sanity,
            redeemers=[helpers[key] for key in redeemer_ids if key in helpers],
            legends=[helpers[key] for key in legend_ids if key in helpers],
            body=refs.get(son.body_entity_id) if son is not None and son.body_entity_id is not None else None,
            anchor_world=refs.get(god.anchor_world_id) if god is not None and god.anchor_world_id is not None else None,
            anchor_star=refs.get(god.anchor_star_id) if god is not None and god.anchor_star_id is not None else None,
            star_modifiers=[
                StarModifierView(
                    id=row.id,
                    source=row.source,
                    luminosity_pct=row.luminosity_pct,
                    age_epochs=row.age_epochs,
                    aged=row.aged,
                    decay=row.decay,
                    epoch=row.epoch,
                    cause=refs.get(row.cause_node_id) if row.cause_node_id is not None else None,
                    locked=row.locked,
                )
                for row in modifiers
            ],
            luminosity_shift=sum(row.luminosity_pct for row in modifiers),
            luminosity_shift_max=LUMINOSITY_SHIFT_MAX,
        )


@router.get("/transformations", response_model=TransformTimelineView)
async def transformation_timeline(services: ServicesDep) -> TransformTimelineView:
    async with reader(services) as session:
        epoch = (await CosmosRepository(session).require_cosmos()).epoch
        rows = list(await session.scalars(select(TransformationRow).order_by(TransformationRow.epoch.desc(), TransformationRow.id.desc())))
        prospects = list(await session.scalars(select(TransformProspectRow).order_by(TransformProspectRow.progress.desc(), TransformProspectRow.id)))
        subjects = await node_refs(session, [row.subject_node_id for row in prospects])
        return TransformTimelineView(
            epoch=epoch,
            kinds=[
                TransformKindView(kind=kind, source=spec.source, target=spec.target, existing=spec.existing, watched=spec.watched, warned=spec.warned)
                for kind, spec in TRANSFORMS.items()
            ],
            transformations=await transformation_views(session, rows, epoch),
            prospects=[prospect_view(row) for row in prospects],
            subjects=[subjects[key] for key in sorted(subjects)],
        )
