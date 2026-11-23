from collections.abc import Iterable
from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.customs import (
    AgeSetView,
    BodyMarkView,
    BorderView,
    CategoryView,
    CommuteView,
    CooperativeView,
    CustomsNodeView,
    EvidenceView,
    GradeDutyView,
    IntoxicantView,
    MarkCustomView,
    MeasureView,
    MembershipView,
    NameFormView,
    NamingCustomView,
    ReliefView,
    RevivalView,
    TavernView,
    TimeBudgetView,
    WelfareView,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.customs import (
    AgeSetMemberRow,
    AgeSetRow,
    BodyMarkRow,
    BorderControlRow,
    CommuteRow,
    CooperativeRow,
    EvidenceRow,
    GradeDutyRow,
    IntoxicantCustomRow,
    MarkCustomRow,
    MeasureStandardRow,
    MembershipCategoryRow,
    MembershipRow,
    NameFormRow,
    NamingCustomRow,
    PoorReliefRow,
    RevivalRow,
    TavernRow,
    TimeBudgetRow,
    WelfareRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.node import NodeKind
from aerona.engine.body.customs import people_of

router = APIRouter(tags=["customs"])
NodeId = Annotated[int, Path(ge=1)]


def at(refs: dict[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


def ref(refs: dict[int, NodeRef], node_id: int) -> NodeRef:
    return refs[node_id] if node_id in refs else NodeRef(id=node_id, kind=NodeKind.ENTITY, name="a lost record")


async def refs_of(session: AsyncSession, ids: Iterable[int | None]) -> dict[int, NodeRef]:
    return await node_refs(session, sorted({value for value in ids if value is not None}))


@router.get("/customs/of/{node_id}", response_model=CustomsNodeView)
async def node_customs(services: ServicesDep, node_id: NodeId) -> CustomsNodeView:
    async with reader(services) as session:
        own = await node_refs(session, [node_id])
        if node_id not in own:
            raise NotFoundError("No such thing.")
        entity = await session.get(EntityRow, node_id)
        folk_row = await people_of(session, entity) if entity is not None else None
        folk = folk_row.id if folk_row is not None else -1
        revivals = list(await session.scalars(select(RevivalRow).where(RevivalRow.people_entity_id == folk).order_by(RevivalRow.id.desc())))
        intoxicants = list(
            await session.scalars(select(IntoxicantCustomRow).where(IntoxicantCustomRow.people_entity_id == folk).order_by(IntoxicantCustomRow.intoxicant))
        )
        mark_customs = list(await session.scalars(select(MarkCustomRow).where(MarkCustomRow.people_entity_id == folk).order_by(MarkCustomRow.kind)))
        marks = list(await session.scalars(select(BodyMarkRow).where(BodyMarkRow.holder_node_id == node_id).order_by(BodyMarkRow.id.desc())))
        budgets = list(
            await session.scalars(
                select(TimeBudgetRow).where(TimeBudgetRow.people_entity_id == folk).order_by(TimeBudgetRow.social_class, TimeBudgetRow.life_stage)
            )
        )
        naming = await session.get(NamingCustomRow, folk)
        names = list(await session.scalars(select(NameFormRow).where(NameFormRow.holder_node_id == node_id).order_by(NameFormRow.form)))
        sets = list(
            await session.scalars(select(AgeSetRow).where(AgeSetRow.people_entity_id == folk).order_by(AgeSetRow.initiated_from.desc(), AgeSetRow.id.desc()))
        )
        sizes = dict((await session.execute(select(AgeSetMemberRow.age_set_id, func.count()).group_by(AgeSetMemberRow.age_set_id))).all())
        member = await session.get(AgeSetMemberRow, node_id)
        hosted = select(StructureProfileRow.structure_entity_id).where(
            or_(StructureProfileRow.host_entity_id == node_id, StructureProfileRow.structure_entity_id == node_id)
        )
        taverns = list(await session.scalars(select(TavernRow).where(TavernRow.structure_entity_id.in_(hosted)).order_by(TavernRow.structure_entity_id)))
        welfare = list(await session.scalars(select(WelfareRow).where(WelfareRow.structure_entity_id.in_(hosted)).order_by(WelfareRow.structure_entity_id)))
        commute = await session.get(CommuteRow, node_id)
        duties = (
            list(await session.scalars(select(GradeDutyRow).where(GradeDutyRow.people_entity_id == folk_row.id).order_by(GradeDutyRow.duty)))
            if folk_row is not None
            else []
        )
        cooperative = await session.get(CooperativeRow, node_id)
        cases = select(CrimeCaseRow.id).where(CrimeCaseRow.accused_entity_id == node_id)
        evidence = list(
            await session.scalars(
                select(EvidenceRow).where(or_(EvidenceRow.points_to_node_id == node_id, EvidenceRow.case_id.in_(cases))).order_by(EvidenceRow.id.desc())
            )
        )
        categories = list(
            await session.scalars(
                select(MembershipCategoryRow).where(MembershipCategoryRow.polity_entity_id == node_id).order_by(MembershipCategoryRow.category)
            )
        )
        membership = await session.get(MembershipRow, node_id)
        border = await session.get(BorderControlRow, node_id)
        relief = await session.get(PoorReliefRow, node_id)
        measures = await session.get(MeasureStandardRow, node_id)
        refs = await refs_of(
            session,
            [
                node_id,
                folk_row.id if folk_row is not None else None,
                *(item for row in revivals for item in (row.dominant_entity_id, row.prophet_node_id)),
                *(item for row in taverns for item in (row.structure_entity_id, row.keeper_node_id)),
                *(item for row in welfare for item in (row.structure_entity_id, row.patron_node_id)),
                *(row.points_to_node_id for row in evidence),
                membership.polity_entity_id if membership is not None else None,
            ],
        )
    return CustomsNodeView(
        node=ref(refs, node_id),
        people=at(refs, folk_row.id if folk_row is not None else None),
        revivals=[
            RevivalView(
                id=row.id,
                dominant=at(refs, row.dominant_entity_id),
                way=row.way,
                stage=row.stage,
                goal=row.goal,
                strength=row.strength,
                prophet=at(refs, row.prophet_node_id),
                started_epoch=row.started_epoch,
                ended_epoch=row.ended_epoch,
                locked=row.locked,
            )
            for row in revivals
        ],
        intoxicants=[IntoxicantView.model_validate(row, from_attributes=True) for row in intoxicants],
        mark_customs=[MarkCustomView.model_validate(row, from_attributes=True) for row in mark_customs],
        marks=[BodyMarkView.model_validate(row, from_attributes=True) for row in marks],
        budgets=[TimeBudgetView.model_validate(row, from_attributes=True) for row in budgets],
        naming=NamingCustomView.model_validate(naming, from_attributes=True) if naming is not None else None,
        names=[NameFormView.model_validate(row, from_attributes=True) for row in names],
        age_sets=[
            AgeSetView(
                id=row.id,
                name=row.name,
                initiated_from=row.initiated_from,
                initiated_to=row.initiated_to,
                grade=row.grade,
                promoted_epoch=row.promoted_epoch,
                members=int(sizes.get(row.id, 0)),
                locked=row.locked,
            )
            for row in sets
        ],
        grade_duties=[GradeDutyView(duty=row.duty, grade=row.grade, held=bool(row.locked)) for row in duties],
        age_set_id=member.age_set_id if member is not None else None,
        taverns=[
            TavernView(
                structure=ref(refs, row.structure_entity_id),
                keeper=at(refs, row.keeper_node_id),
                patrons=row.patrons,
                brawls=row.brawls,
                lodging=row.lodging,
                rumours=row.rumours,
                locked=row.locked,
            )
            for row in taverns
        ],
        welfare=[
            WelfareView(
                structure=ref(refs, row.structure_entity_id), patron=at(refs, row.patron_node_id), inmates=row.inmates, upkeep=row.upkeep, locked=row.locked
            )
            for row in welfare
        ],
        commute=CommuteView.model_validate(commute, from_attributes=True) if commute is not None else None,
        cooperative=CooperativeView.model_validate(cooperative, from_attributes=True) if cooperative is not None else None,
        evidence=[
            EvidenceView(
                id=row.id,
                case_id=row.case_id,
                kind=row.kind,
                points_to=at(refs, row.points_to_node_id),
                reliability=row.reliability,
                forged=row.forged,
                found_epoch=row.found_epoch,
                locked=row.locked,
            )
            for row in evidence
        ],
        categories=[CategoryView.model_validate(row, from_attributes=True) for row in categories],
        membership=MembershipView(
            realm=ref(refs, membership.polity_entity_id),
            category=membership.category,
            path=membership.path,
            since_epoch=membership.since_epoch,
            locked=membership.locked,
        )
        if membership is not None
        else None,
        border=BorderView.model_validate(border, from_attributes=True) if border is not None else None,
        relief=ReliefView.model_validate(relief, from_attributes=True) if relief is not None else None,
        measures=MeasureView.model_validate(measures, from_attributes=True) if measures is not None else None,
    )
