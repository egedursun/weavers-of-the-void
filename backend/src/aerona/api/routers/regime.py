from collections.abc import Iterable
from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.records import NodeRef
from aerona.api.schemas.regime import (
    AcademicFreedomView,
    BreedingPlanView,
    CoalitionMemberView,
    CosmosRegimeView,
    CredentialView,
    DiscipleView,
    ExaminationView,
    ExamSittingView,
    LineageSegmentView,
    PatronageTieView,
    PowerBaseView,
    RealmRuleView,
    RealmSeatView,
    RegimeNodeView,
    RegimeView,
    SchoolRivalView,
    SchoolView,
    VenalOfficeView,
)
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.cycles import LongPlanRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.tables.regime import (
    AcademicFreedomRow,
    BreedingPlanRow,
    CoalitionMemberRow,
    CredentialRow,
    ExaminationRow,
    ExamSittingRow,
    LineageSegmentRow,
    PatronageTieRow,
    PowerBaseRow,
    RegimeRow,
    SchoolLineageRow,
    SchoolMemberRow,
    VenalOfficeRow,
)
from aerona.domain.enums.node import NodeKind
from aerona.engine.regime.book import dominant

router = APIRouter(tags=["regime"])
NodeId = Annotated[int, Path(ge=1)]
COSMOS_SITTINGS = 40


def at(refs: dict[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


def ref(refs: dict[int, NodeRef], node_id: int) -> NodeRef:
    return refs[node_id] if node_id in refs else NodeRef(id=node_id, kind=NodeKind.ENTITY, name="a lost record")


async def refs_of(session: AsyncSession, ids: Iterable[int | None]) -> dict[int, NodeRef]:
    return await node_refs(session, sorted({value for value in ids if value is not None}))


def regime_view(row: RegimeRow, refs: dict[int, NodeRef]) -> RegimeView:
    return RegimeView(
        selectorate=row.selectorate,
        selectorate_size=row.selectorate_size,
        coalition_size=row.coalition_size,
        coalition_loyalty=row.coalition_loyalty,
        public_share=row.public_share,
        traditional=row.traditional,
        charismatic=row.charismatic,
        rational=row.rational,
        dominant=dominant(row),
        founder=at(refs, row.founder_entity_id),
        ruler=at(refs, row.ruler_entity_id),
        routinisation=row.routinisation,
        crisis_epoch=row.crisis_epoch,
        horizon=row.horizon,
        extraction=row.extraction,
        institutions=row.institutions,
        leadership=row.leadership,
        rotation=row.rotation,
        parallel_guard=row.parallel_guard,
        loyalty_promotion=row.loyalty_promotion,
        hostages=row.hostages,
        updated_epoch=row.updated_epoch,
        locked=list(row.locked),
    )


def base_view(row: PowerBaseRow, refs: dict[int, NodeRef]) -> PowerBaseView:
    return PowerBaseView(
        mortal=ref(refs, row.mortal_entity_id),
        polity=at(refs, row.polity_entity_id),
        holdings=row.holdings,
        troops=row.troops,
        offices=row.offices,
        wealth=row.wealth,
        popularity=row.popularity,
        total=row.total,
        threat=row.threat,
        stance=row.stance,
        updated_epoch=row.updated_epoch,
        locked=list(row.locked),
    )


def segment_view(row: LineageSegmentRow, refs: dict[int, NodeRef]) -> LineageSegmentView:
    return LineageSegmentView(
        house=ref(refs, row.house_entity_id),
        level=row.level,
        tribe=at(refs, row.tribe_entity_id),
        backs=at(refs, row.backs_entity_id),
        since_epoch=row.since_epoch,
        locked=list(row.locked),
    )


def freedom_view(row: AcademicFreedomRow, refs: dict[int, NodeRef]) -> AcademicFreedomView:
    return AcademicFreedomView(
        structure=ref(refs, row.structure_entity_id),
        level=row.level,
        orthodoxy=at(refs, row.orthodoxy_node_id),
        suppressed=row.suppressed,
        updated_epoch=row.updated_epoch,
        locked=list(row.locked),
    )


def sitting_view(row: ExamSittingRow, refs: dict[int, NodeRef]) -> ExamSittingView:
    return ExamSittingView(
        id=row.id, polity=ref(refs, row.polity_entity_id), candidates=row.candidates, passed=row.passed, mark=row.mark, epoch=row.epoch, locked=list(row.locked)
    )


async def school_views(session: AsyncSession, schools: list[SchoolLineageRow]) -> list[SchoolView]:
    members = {
        school.id: list(
            await session.scalars(
                select(SchoolMemberRow).where(SchoolMemberRow.school_id == school.id).order_by(SchoolMemberRow.generation, SchoolMemberRow.mortal_entity_id)
            )
        )
        for school in schools
    }
    names = {row.id: row.name for row in await session.scalars(select(SchoolLineageRow))}
    refs = await refs_of(
        session,
        [
            *(ref_id for school in schools for ref_id in (school.doctrine_entity_id, school.founder_entity_id)),
            *(ref_id for rows in members.values() for row in rows for ref_id in (row.mortal_entity_id, row.master_entity_id)),
        ],
    )
    return [
        SchoolView(
            id=school.id,
            name=school.name,
            doctrine=at(refs, school.doctrine_entity_id),
            founder=at(refs, school.founder_entity_id),
            rival=SchoolRivalView(id=school.rival_id, name=names.get(school.rival_id, "a vanished school")) if school.rival_id is not None else None,
            persecuted=school.persecuted,
            since_epoch=school.since_epoch,
            locked=list(school.locked),
            disciples=[
                DiscipleView(
                    mortal=ref(refs, row.mortal_entity_id),
                    master=at(refs, row.master_entity_id),
                    generation=row.generation,
                    since_epoch=row.since_epoch,
                    locked=list(row.locked),
                )
                for row in members[school.id]
            ],
        )
        for school in schools
    ]


async def venal_of(session: AsyncSession, node_id: int) -> list[tuple[VenalOfficeRow, OfficeRow]]:
    rows = await session.execute(
        select(VenalOfficeRow, OfficeRow)
        .join(OfficeRow, OfficeRow.id == VenalOfficeRow.office_id)
        .where(or_(OfficeRow.polity_entity_id == node_id, OfficeRow.holder_entity_id == node_id, VenalOfficeRow.buyer_entity_id == node_id))
        .order_by(VenalOfficeRow.office_id)
    )
    return [(venal, office) for venal, office in rows.all()]


async def breeding_of(session: AsyncSession, node_id: int) -> list[tuple[BreedingPlanRow, LongPlanRow]]:
    rows = await session.execute(
        select(BreedingPlanRow, LongPlanRow)
        .join(LongPlanRow, LongPlanRow.id == BreedingPlanRow.plan_id)
        .where(or_(BreedingPlanRow.house_entity_id == node_id, LongPlanRow.holder_node_id == node_id, BreedingPlanRow.claim_polity_id == node_id))
        .order_by(BreedingPlanRow.plan_id)
    )
    return [(plan, design) for plan, design in rows.all()]


async def schools_of(session: AsyncSession, node_id: int) -> list[SchoolLineageRow]:
    joined = set(await session.scalars(select(SchoolMemberRow.school_id).where(SchoolMemberRow.mortal_entity_id == node_id)))
    rows = await session.scalars(
        select(SchoolLineageRow)
        .where(or_(SchoolLineageRow.founder_entity_id == node_id, SchoolLineageRow.doctrine_entity_id == node_id, SchoolLineageRow.id.in_(joined)))
        .order_by(SchoolLineageRow.id)
    )
    return list(rows)


@router.get("/regime/of/{node_id}", response_model=RegimeNodeView)
async def node_regime(services: ServicesDep, node_id: NodeId) -> RegimeNodeView:
    async with reader(services) as session:
        own = await node_refs(session, [node_id])
        if node_id not in own:
            raise NotFoundError("No such thing.")
        regime = await session.get(RegimeRow, node_id)
        members = list(
            await session.scalars(
                select(CoalitionMemberRow)
                .where(or_(CoalitionMemberRow.polity_entity_id == node_id, CoalitionMemberRow.mortal_entity_id == node_id))
                .order_by(CoalitionMemberRow.polity_entity_id, CoalitionMemberRow.mortal_entity_id)
            )
        )
        ties = list(
            await session.scalars(
                select(PatronageTieRow)
                .where(or_(PatronageTieRow.patron_node_id == node_id, PatronageTieRow.client_entity_id == node_id))
                .order_by(PatronageTieRow.id)
            )
        )
        seats = list(await session.scalars(select(OfficeRow).where(OfficeRow.polity_entity_id == node_id).order_by(OfficeRow.id)))
        venal = await venal_of(session, node_id)
        power_base = await session.get(PowerBaseRow, node_id)
        bases = list(await session.scalars(select(PowerBaseRow).where(PowerBaseRow.polity_entity_id == node_id).order_by(PowerBaseRow.threat.desc())))
        lineage = await session.get(LineageSegmentRow, node_id)
        kin_lines = list(
            await session.scalars(
                select(LineageSegmentRow)
                .where(or_(LineageSegmentRow.tribe_entity_id == node_id, LineageSegmentRow.backs_entity_id == node_id))
                .order_by(LineageSegmentRow.house_entity_id)
            )
        )
        breeding = await breeding_of(session, node_id)
        examination = await session.get(ExaminationRow, node_id)
        sittings = list(await session.scalars(select(ExamSittingRow).where(ExamSittingRow.polity_entity_id == node_id).order_by(ExamSittingRow.epoch.desc())))
        credentials = list(
            await session.scalars(
                select(CredentialRow)
                .where(or_(CredentialRow.mortal_entity_id == node_id, CredentialRow.granter_node_id == node_id))
                .order_by(CredentialRow.id.desc())
            )
        )
        freedom = await session.get(AcademicFreedomRow, node_id)
        refs = await refs_of(
            session,
            [
                node_id,
                *((regime.founder_entity_id, regime.ruler_entity_id) if regime is not None else ()),
                *(ref_id for row in members for ref_id in (row.polity_entity_id, row.mortal_entity_id)),
                *(ref_id for row in ties for ref_id in (row.patron_node_id, row.client_entity_id)),
                *(row.holder_entity_id for row in seats),
                *(ref_id for venal_row, office in venal for ref_id in (venal_row.buyer_entity_id, office.holder_entity_id, office.polity_entity_id)),
                *(ref_id for row in [*bases, *([power_base] if power_base is not None else [])] for ref_id in (row.mortal_entity_id, row.polity_entity_id)),
                *(
                    ref_id
                    for row in [*kin_lines, *([lineage] if lineage is not None else [])]
                    for ref_id in (row.house_entity_id, row.tribe_entity_id, row.backs_entity_id)
                ),
                *(ref_id for plan, design in breeding for ref_id in (plan.house_entity_id, plan.claim_polity_id, design.holder_node_id)),
                *(row.polity_entity_id for row in sittings),
                *(ref_id for row in credentials for ref_id in (row.mortal_entity_id, row.granter_node_id)),
                *((freedom.structure_entity_id, freedom.orthodoxy_node_id) if freedom is not None else ()),
            ],
        )
        return RegimeNodeView(
            node=own[node_id],
            regime=regime_view(regime, refs) if regime is not None else None,
            members=[
                CoalitionMemberView(
                    polity=ref(refs, row.polity_entity_id),
                    mortal=ref(refs, row.mortal_entity_id),
                    reward=row.reward,
                    loyalty=row.loyalty,
                    since_epoch=row.since_epoch,
                    locked=list(row.locked),
                )
                for row in members
            ],
            ties=[
                PatronageTieView(
                    id=row.id,
                    patron=ref(refs, row.patron_node_id),
                    client=ref(refs, row.client_entity_id),
                    role=row.role,
                    strength=row.strength,
                    since_epoch=row.since_epoch,
                    locked=list(row.locked),
                )
                for row in ties
            ],
            seats=[RealmSeatView(office_id=row.id, kind=row.kind, holder=at(refs, row.holder_entity_id)) for row in seats],
            offices=[
                VenalOfficeView(
                    office_id=venal_row.office_id,
                    office_kind=office.kind,
                    polity=ref(refs, office.polity_entity_id),
                    holder=at(refs, office.holder_entity_id),
                    price=venal_row.price,
                    buyer=at(refs, venal_row.buyer_entity_id),
                    sinecure=venal_row.sinecure,
                    recouped=venal_row.recouped,
                    sold_epoch=venal_row.sold_epoch,
                    locked=list(venal_row.locked),
                )
                for venal_row, office in venal
            ],
            power_base=base_view(power_base, refs) if power_base is not None else None,
            bases=[base_view(row, refs) for row in bases],
            lineage=segment_view(lineage, refs) if lineage is not None else None,
            kin_lines=[segment_view(row, refs) for row in kin_lines],
            breeding=[
                BreedingPlanView(
                    plan_id=plan.plan_id,
                    name=design.name,
                    holder=at(refs, design.holder_node_id),
                    house=ref(refs, plan.house_entity_id),
                    locus=plan.locus,
                    allele=plan.allele,
                    target_share=plan.target_share,
                    claim_polity=at(refs, plan.claim_polity_id),
                    matches=plan.matches,
                    love_matches=plan.love_matches,
                    barren=plan.barren,
                    concealed=plan.concealed,
                    progress=design.progress,
                    steps=design.steps,
                    status=design.status,
                    locked=list(plan.locked),
                )
                for plan, design in breeding
            ],
            examination=ExaminationView(
                interval=examination.interval,
                quota=examination.quota,
                pass_mark=examination.pass_mark,
                demand=examination.demand,
                last_epoch=examination.last_epoch,
                locked=list(examination.locked),
            )
            if examination is not None
            else None,
            sittings=[sitting_view(row, refs) for row in sittings],
            credentials=[
                CredentialView(
                    id=row.id,
                    mortal=ref(refs, row.mortal_entity_id),
                    kind=row.kind,
                    granter=at(refs, row.granter_node_id),
                    skill=row.skill,
                    epoch=row.epoch,
                    locked=list(row.locked),
                )
                for row in credentials
            ],
            freedom=freedom_view(freedom, refs) if freedom is not None else None,
            schools=await school_views(session, await schools_of(session, node_id)),
        )


@router.get("/regime/cosmos", response_model=CosmosRegimeView)
async def cosmos_regime(services: ServicesDep) -> CosmosRegimeView:
    async with reader(services) as session:
        regimes = list(await session.scalars(select(RegimeRow).order_by(RegimeRow.polity_entity_id)))
        bases = list(await session.scalars(select(PowerBaseRow).order_by(PowerBaseRow.threat.desc(), PowerBaseRow.mortal_entity_id)))
        freedoms = list(await session.scalars(select(AcademicFreedomRow).order_by(AcademicFreedomRow.level, AcademicFreedomRow.structure_entity_id)))
        sittings = list(await session.scalars(select(ExamSittingRow).order_by(ExamSittingRow.epoch.desc(), ExamSittingRow.id.desc()).limit(COSMOS_SITTINGS)))
        schools = list(await session.scalars(select(SchoolLineageRow).order_by(SchoolLineageRow.id)))
        refs = await refs_of(
            session,
            [
                *(row.polity_entity_id for row in regimes),
                *(ref_id for row in bases for ref_id in (row.mortal_entity_id, row.polity_entity_id)),
                *(ref_id for row in freedoms for ref_id in (row.structure_entity_id, row.orthodoxy_node_id)),
                *(row.polity_entity_id for row in sittings),
            ],
        )
        return CosmosRegimeView(
            realms=[
                RealmRuleView(
                    polity=ref(refs, row.polity_entity_id),
                    selectorate=row.selectorate,
                    selectorate_size=row.selectorate_size,
                    coalition_size=row.coalition_size,
                    public_share=row.public_share,
                    horizon=row.horizon,
                    dominant=dominant(row),
                    routinisation=row.routinisation,
                    leadership=row.leadership,
                )
                for row in regimes
            ],
            bases=[base_view(row, refs) for row in bases],
            freedoms=[freedom_view(row, refs) for row in freedoms],
            schools=await school_views(session, schools),
            sittings=[sitting_view(row, refs) for row in sittings],
        )
