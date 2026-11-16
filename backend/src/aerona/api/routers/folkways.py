from collections.abc import Iterable
from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.folkways import (
    AccusationView,
    CharmView,
    DecisionBiasView,
    DietView,
    FolkwaysNodeView,
    HuntView,
    LuckBeliefView,
    MethodView,
    MishapView,
    NeedView,
    NutritionView,
    PurityRankView,
    PurityView,
    SourceView,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folkways import (
    AccusationRow,
    BiasWeightRow,
    CharmRow,
    DietRow,
    ImpuritySourceRow,
    LuckBeliefRow,
    MishapRow,
    NutrientNeedRow,
    NutritionScoreRow,
    PurificationRow,
    PurityRankRow,
    PurityRow,
    WitchHuntRow,
)
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.node import NodeKind
from aerona.engine.body.customs import people_of

router = APIRouter(tags=["folkways"])
NodeId = Annotated[int, Path(ge=1)]


def at(refs: dict[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


def ref(refs: dict[int, NodeRef], node_id: int) -> NodeRef:
    return refs[node_id] if node_id in refs else NodeRef(id=node_id, kind=NodeKind.ENTITY, name="a lost record")


async def refs_of(session: AsyncSession, ids: Iterable[int | None]) -> dict[int, NodeRef]:
    return await node_refs(session, sorted({value for value in ids if value is not None}))


async def people_for(session: AsyncSession, node_id: int) -> int | None:
    entity = await session.get(EntityRow, node_id)
    folk = await people_of(session, entity) if entity is not None else None
    return folk.id if folk is not None else None


@router.get("/folkways/of/{node_id}", response_model=FolkwaysNodeView)
async def node_folkways(services: ServicesDep, node_id: NodeId) -> FolkwaysNodeView:
    async with reader(services) as session:
        own = await node_refs(session, [node_id])
        if node_id not in own:
            raise NotFoundError("No such thing.")
        people = await people_for(session, node_id)
        folk = people if people is not None else -1
        diet = await session.get(DietRow, node_id)
        score = await session.get(NutritionScoreRow, node_id)
        purity = await session.get(PurityRow, node_id)
        needs = list(await session.scalars(select(NutrientNeedRow).where(NutrientNeedRow.people_entity_id == folk).order_by(NutrientNeedRow.nutrient)))
        biases = list(await session.scalars(select(BiasWeightRow).where(BiasWeightRow.holder_node_id == node_id).order_by(BiasWeightRow.bias)))
        ranks = list(
            await session.scalars(select(PurityRankRow).where(PurityRankRow.people_entity_id == folk).order_by(PurityRankRow.standing.desc(), PurityRankRow.id))
        )
        sources = list(await session.scalars(select(ImpuritySourceRow).where(ImpuritySourceRow.people_entity_id == folk).order_by(ImpuritySourceRow.source)))
        methods = list(await session.scalars(select(PurificationRow).where(PurificationRow.people_entity_id == folk).order_by(PurificationRow.method)))
        touching = or_(MishapRow.settlement_entity_id == node_id, MishapRow.victim_node_id == node_id, MishapRow.cause_node_id == node_id)
        mishaps = list(await session.scalars(select(MishapRow).where(touching).order_by(MishapRow.id.desc())))
        beliefs = list(await session.scalars(select(LuckBeliefRow).where(LuckBeliefRow.people_entity_id == folk).order_by(LuckBeliefRow.id)))
        owned = select(BondRow.target_node_id).where(BondRow.source_node_id == node_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
        charms = list(
            await session.scalars(
                select(CharmRow).where(or_(CharmRow.item_entity_id == node_id, CharmRow.item_entity_id.in_(owned))).order_by(CharmRow.item_entity_id)
            )
        )
        accused = or_(AccusationRow.settlement_entity_id == node_id, AccusationRow.accuser_node_id == node_id, AccusationRow.accused_node_id == node_id)
        accusations = list(await session.scalars(select(AccusationRow).where(accused).order_by(AccusationRow.id.desc())))
        hunts = list(await session.scalars(select(WitchHuntRow).where(WitchHuntRow.settlement_entity_id == node_id).order_by(WitchHuntRow.id.desc())))
        refs = await refs_of(
            session,
            [
                node_id,
                people,
                *(item for row in mishaps for item in (row.settlement_entity_id, row.victim_node_id, row.cause_node_id)),
                *(node for row in mishaps for node in row.witnesses),
                *(row.item_entity_id for row in charms),
                *(item for row in accusations for item in (row.settlement_entity_id, row.accuser_node_id, row.accused_node_id)),
            ],
        )
    return FolkwaysNodeView(
        node=ref(refs, node_id),
        people=at(refs, people),
        diet=DietView.model_validate(diet, from_attributes=True) if diet is not None else None,
        nutrition=NutritionView.model_validate(score, from_attributes=True) if score is not None else None,
        needs=[NeedView.model_validate(row, from_attributes=True) for row in needs],
        biases=[DecisionBiasView.model_validate(row, from_attributes=True) for row in biases],
        purity=PurityView.model_validate(purity, from_attributes=True) if purity is not None else None,
        ranks=[PurityRankView.model_validate(row, from_attributes=True) for row in ranks],
        sources=[SourceView.model_validate(row, from_attributes=True) for row in sources],
        methods=[MethodView.model_validate(row, from_attributes=True) for row in methods],
        mishaps=[
            MishapView(
                id=row.id,
                town=ref(refs, row.settlement_entity_id),
                victim=at(refs, row.victim_node_id),
                cause=at(refs, row.cause_node_id),
                kind=row.kind,
                true_cause=row.true_cause,
                explained=row.explained,
                attribution=row.attribution,
                response=row.response,
                severity=row.severity,
                died=row.died,
                witnesses=[refs[node] for node in row.witnesses if node in refs],
                epoch=row.epoch,
                locked=row.locked,
            )
            for row in mishaps
        ],
        beliefs=[LuckBeliefView.model_validate(row, from_attributes=True) for row in beliefs],
        charms=[CharmView(item=ref(refs, row.item_entity_id), power=row.power, real=row.real, strength=row.strength, locked=row.locked) for row in charms],
        accusations=[
            AccusationView(
                id=row.id,
                town=at(refs, row.settlement_entity_id),
                accuser=at(refs, row.accuser_node_id),
                accused=ref(refs, row.accused_node_id),
                mishap_id=row.mishap_id,
                hunt_id=row.hunt_id,
                case_id=row.case_id,
                outcome=row.outcome,
                guilty_in_truth=row.guilty_in_truth,
                opened_epoch=row.opened_epoch,
                closed_epoch=row.closed_epoch,
                locked=row.locked,
            )
            for row in accusations
        ],
        hunts=[HuntView.model_validate(row, from_attributes=True) for row in hunts],
    )
