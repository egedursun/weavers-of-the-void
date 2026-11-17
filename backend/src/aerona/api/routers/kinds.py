from typing import Annotated, Any

from fastapi import APIRouter, Path, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.kinds import AuthoredKindRecord, KindCategoryInfo, KindConceptInfo, KindHoldingView, KindPropertyInfo, KindValue, WaysOfLifeView
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.kind_concepts.registry import CONCEPTS
from aerona.db.kind_concepts.spec import ConceptSpec, KindProperty
from aerona.db.tables.kinds import KindHoldingRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.kinds import KindConcept

router = APIRouter(tags=["kinds"])
NodeId = Annotated[int, Path(ge=1)]


def concept_info(spec: ConceptSpec) -> KindConceptInfo:
    return KindConceptInfo(
        concept=spec.concept,
        label=spec.label,
        plural=spec.plural,
        hint=spec.hint,
        categories=[KindCategoryInfo(key=key, label=label) for key, label in spec.category_labels.items()],
        properties=[property_info(item) for item in spec.properties],
    )


def property_info(item: KindProperty) -> KindPropertyInfo:
    options = [KindCategoryInfo(key=key, label=label) for key, label in (item.options or {}).items()]
    return KindPropertyInfo(column=item.column, label=item.label, hint=item.hint, low=item.low, high=item.high, options=options)


def value_of(item: KindProperty, row: Any) -> KindValue:
    value, option, label = item.shown(getattr(row, item.column))
    return KindValue(column=item.column, value=value, option=option, option_label=label)


async def records(session: AsyncSession, spec: ConceptSpec, rows: list[Any]) -> list[AuthoredKindRecord]:
    ids = [row.id for row in rows]
    holdings = list(
        await session.scalars(select(KindHoldingRow).where(KindHoldingRow.concept == spec.concept, KindHoldingRow.kind_id.in_(ids)).order_by(KindHoldingRow.id))
    )
    parents = {
        row.id: row.name
        for row in await session.scalars(select(spec.table).where(spec.table.id.in_([row.derived_from_id for row in rows if row.derived_from_id])))
    }
    nodes = (
        {row.world_id for row in rows if row.world_id} | {row.origin_node_id for row in rows if row.origin_node_id} | {item.holder_node_id for item in holdings}
    )
    refs = await node_refs(session, sorted(nodes))
    held_by: dict[int, list[NodeRef]] = {}
    for item in holdings:
        if item.holder_node_id in refs:
            held_by.setdefault(item.kind_id, []).append(refs[item.holder_node_id])
    return [
        AuthoredKindRecord(
            id=row.id,
            concept=spec.concept,
            name=row.name,
            description=row.description,
            category=row.category_key(),
            category_label=spec.category_labels[row.category_key()],
            world=refs.get(row.world_id) if row.world_id else None,
            origin=refs.get(row.origin_node_id) if row.origin_node_id else None,
            derived_from_id=row.derived_from_id,
            derived_from_name=parents.get(row.derived_from_id) if row.derived_from_id else None,
            built_in=row.built_in,
            retired=row.retired,
            created_epoch=row.created_epoch,
            locked=list(row.locked),
            values=[value_of(item, row) for item in spec.properties],
            holders=held_by.get(row.id, []),
        )
        for row in rows
    ]


@router.get("/kinds/concepts", response_model=list[KindConceptInfo])
async def kind_concepts() -> list[KindConceptInfo]:
    return [concept_info(spec) for spec in CONCEPTS.values()]


@router.get("/kinds/of/{node_id}", response_model=WaysOfLifeView)
async def ways_of_life(services: ServicesDep, node_id: NodeId) -> WaysOfLifeView:
    async with reader(services) as session:
        if await session.get(NodeRow, node_id) is None:
            raise NotFoundError("No such thing.")
        holdings = list(
            await session.scalars(select(KindHoldingRow).where(KindHoldingRow.holder_node_id == node_id).order_by(KindHoldingRow.concept, KindHoldingRow.id))
        )
        views: list[KindHoldingView] = []
        for item in holdings:
            spec = CONCEPTS.get(item.concept)
            kind = await session.get(spec.table, item.kind_id) if spec is not None else None
            if spec is None or kind is None:
                continue
            views.append(
                KindHoldingView(
                    id=item.id,
                    concept=item.concept,
                    kind_id=kind.id,
                    kind_name=kind.name,
                    category_label=spec.category_labels[kind.category_key()],
                    stance=item.stance,
                    strength=item.strength,
                    spread=item.spread,
                    since_epoch=item.since_epoch,
                    locked=list(item.locked),
                )
            )
        made: list[AuthoredKindRecord] = []
        for spec in CONCEPTS.values():
            rows = list(
                await session.scalars(
                    select(spec.table).where((spec.table.origin_node_id == node_id) | (spec.table.world_id == node_id)).order_by(spec.table.id)
                )
            )
            made.extend(await records(session, spec, rows))
        refs = await node_refs(session, [node_id])
        return WaysOfLifeView(node=refs[node_id], holdings=views, made=made)


@router.get("/kinds/{concept}", response_model=list[AuthoredKindRecord])
async def kinds_of_concept(services: ServicesDep, concept: KindConcept, world_id: Annotated[int | None, Query(ge=1)] = None) -> list[AuthoredKindRecord]:
    spec = CONCEPTS.get(concept)
    if spec is None:
        raise NotFoundError("No such kind of thing.")
    async with reader(services) as session:
        statement = select(spec.table).order_by(spec.table.id)
        if world_id is not None:
            statement = statement.where((spec.table.world_id == world_id) | spec.table.world_id.is_(None))
        return await records(session, spec, list(await session.scalars(statement)))
