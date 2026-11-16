from collections.abc import Iterable
from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.cycles import (
    AllianceView,
    BondMarketView,
    CampView,
    CasteView,
    ChallengeView,
    CircuitView,
    ConfederationView,
    CosmosCyclesView,
    CyclesView,
    FrontierView,
    GiftRecordView,
    IndentureView,
    KinshipView,
    LegacyView,
    ManumissionView,
    OfferingLedgerView,
    PlanView,
    ReadingView,
    RealmCycleView,
    ReproductionView,
    SolidarityView,
    StressPartView,
    StressView,
    UnionView,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.catalog.techniques import TECHNIQUES
from aerona.core.errors import NotFoundError
from aerona.db.tables.cycles import (
    AsabiyyaRow,
    CampRow,
    ChallengeRow,
    CircuitRow,
    ConfederationRow,
    DivineDebtRow,
    GiftRow,
    IndentureRow,
    KinshipSystemRow,
    LegacyTraitRow,
    LongPlanRow,
    ManumissionRow,
    MarriageAllianceRow,
    MortalCasteRow,
    PeopleReproductionRow,
    PolityStressRow,
    SlaveMarketRow,
    StressReadingRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.unions import UnionCustomRow
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.cycles import LegacyKind, StressComponent
from aerona.domain.enums.mind import ValueAxis
from aerona.engine.cycles.gifts import balance
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import homes_of

router = APIRouter(tags=["cycles"])
NAMED_LEGACIES = frozenset({LegacyKind.BELIEF, LegacyKind.ART_FORM})
NodeId = Annotated[int, Path(ge=1)]
PARTS = {
    StressComponent.POPULATION_PRESSURE: "pressure",
    StressComponent.IMMISERATION: "immiseration",
    StressComponent.ELITE_OVERPRODUCTION: "elite_overproduction",
    StressComponent.FISCAL_DISTRESS: "fiscal_distress",
}


def at(refs: dict[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


def need(refs: dict[int, NodeRef], node_id: int) -> NodeRef:
    found = refs.get(node_id)
    if found is None:
        raise NotFoundError("A record names a thing that is gone.")
    return found


def stress_view(row: PolityStressRow) -> StressView:
    return StressView(
        parts=[StressPartView(component=component, value=int(getattr(row, field))) for component, field in PARTS.items()],
        psi=row.psi,
        aspirants=row.aspirants,
        positions=row.positions,
        challenge=row.challenge,
        phase=row.phase,
        updated_epoch=row.updated_epoch,
        locked=list(row.locked),
    )


def reading_view(row: StressReadingRow) -> ReadingView:
    return ReadingView(
        epoch=row.epoch,
        pressure=row.pressure,
        immiseration=row.immiseration,
        elite_overproduction=row.elite_overproduction,
        fiscal_distress=row.fiscal_distress,
        psi=row.psi,
        phase=row.phase,
    )


def plan_view(row: LongPlanRow, refs: dict[int, NodeRef]) -> PlanView:
    return PlanView(
        id=row.id,
        holder=need(refs, row.holder_node_id),
        author=at(refs, row.author_node_id),
        carrier=at(refs, row.carrier_node_id),
        target=at(refs, row.target_node_id),
        kind=row.kind,
        name=row.name,
        steps=row.steps,
        progress=row.progress,
        step_cost=row.step_cost,
        secrecy=row.secrecy,
        exposed=row.exposed,
        status=row.status,
        started_epoch=row.started_epoch,
        finished_epoch=row.finished_epoch,
        locked=list(row.locked),
    )


def gift_view(row: GiftRow, refs: dict[int, NodeRef]) -> GiftRecordView:
    return GiftRecordView(
        id=row.id,
        giver=need(refs, row.giver_node_id),
        receiver=need(refs, row.receiver_node_id),
        value=row.value,
        occasion=row.occasion,
        item=at(refs, row.item_entity_id),
        state=row.state,
        answers_gift_id=row.answers_gift_id,
        due_epoch=row.due_epoch,
        settled_epoch=row.settled_epoch,
        epoch=row.epoch,
        locked=list(row.locked),
    )


def circuit_view(row: CircuitRow, refs: dict[int, NodeRef]) -> CircuitView:
    return CircuitView(
        id=row.id,
        name=row.name,
        item=at(refs, row.item_entity_id),
        stops=[refs[stop] for stop in row.stops if stop in refs],
        position=row.position,
        passes=row.passes,
        started_epoch=row.started_epoch,
        locked=list(row.locked),
    )


def confederation_view(row: ConfederationRow, refs: dict[int, NodeRef]) -> ConfederationView:
    return ConfederationView(
        id=row.id,
        name=row.name,
        leader=at(refs, row.leader_entity_id),
        members=[refs[member] for member in row.members if member in refs],
        formed_epoch=row.formed_epoch,
        dissolved_epoch=row.dissolved_epoch,
        locked=list(row.locked),
    )


def legacy_label(row: LegacyTraitRow, refs: dict[int, NodeRef]) -> str:
    if row.kind is LegacyKind.INNOVATION and row.key in Technique._value2member_map_:
        return TECHNIQUES[Technique(row.key)].label
    if row.kind in NAMED_LEGACIES and row.key.isdigit():
        found = refs.get(int(row.key))
        return found.name if found is not None else row.key
    if row.kind is LegacyKind.VALUE and row.key in ValueAxis._value2member_map_:
        return ValueAxis(row.key).value.replace("_", " ")
    return row.key.replace("_", " ")


async def refs_of(session: AsyncSession, ids: Iterable[int | None]) -> dict[int, NodeRef]:
    return await node_refs(session, sorted({value for value in ids if value is not None}))


async def plans_of(session: AsyncSession, node_id: int | None) -> list[LongPlanRow]:
    statement = select(LongPlanRow).order_by(LongPlanRow.id)
    if node_id is not None:
        statement = statement.where(or_(LongPlanRow.holder_node_id == node_id, LongPlanRow.carrier_node_id == node_id, LongPlanRow.target_node_id == node_id))
    return list(await session.scalars(statement))


async def gifts_of(session: AsyncSession, node_id: int | None) -> list[GiftRow]:
    statement = select(GiftRow).order_by(GiftRow.id.desc())
    if node_id is not None:
        statement = statement.where(or_(GiftRow.giver_node_id == node_id, GiftRow.receiver_node_id == node_id))
    return list(await session.scalars(statement))


async def circuits_of(session: AsyncSession, node_id: int | None) -> list[CircuitRow]:
    rows = list(await session.scalars(select(CircuitRow).order_by(CircuitRow.id)))
    return [row for row in rows if node_id is None or node_id in row.stops or node_id == row.item_entity_id]


async def confederations_of(session: AsyncSession, node_id: int | None) -> list[ConfederationRow]:
    rows = list(await session.scalars(select(ConfederationRow).order_by(ConfederationRow.id)))
    return [row for row in rows if node_id is None or node_id in row.members or node_id == row.leader_entity_id]


@router.get("/cycles/of/{node_id}", response_model=CyclesView)
async def node_cycles(services: ServicesDep, node_id: NodeId) -> CyclesView:
    async with reader(services) as session:
        own = await node_refs(session, [node_id])
        if node_id not in own:
            raise NotFoundError("No such thing.")
        stress = await session.get(PolityStressRow, node_id)
        readings = list(await session.scalars(select(StressReadingRow).where(StressReadingRow.polity_entity_id == node_id).order_by(StressReadingRow.epoch)))
        solidarity = await session.get(AsabiyyaRow, node_id)
        challenges = list(await session.scalars(select(ChallengeRow).where(ChallengeRow.holder_entity_id == node_id).order_by(ChallengeRow.id.desc())))
        plans = await plans_of(session, node_id)
        gifts = await gifts_of(session, node_id)
        debts = list(
            await session.scalars(
                select(DivineDebtRow)
                .where(or_(DivineDebtRow.god_node_id == node_id, DivineDebtRow.community_entity_id == node_id))
                .order_by(DivineDebtRow.god_node_id, DivineDebtRow.community_entity_id)
            )
        )
        circuits = await circuits_of(session, node_id)
        alliances = list(
            await session.scalars(
                select(MarriageAllianceRow)
                .where(or_(MarriageAllianceRow.giver_entity_id == node_id, MarriageAllianceRow.taker_entity_id == node_id))
                .order_by(MarriageAllianceRow.giver_entity_id, MarriageAllianceRow.taker_entity_id)
            )
        )
        camp = await session.get(CampRow, node_id)
        confederations = await confederations_of(session, node_id)
        legacies = list(
            await session.scalars(select(LegacyTraitRow).where(LegacyTraitRow.people_entity_id == node_id).order_by(LegacyTraitRow.kind, LegacyTraitRow.key))
        )
        indentures = list(await session.scalars(select(IndentureRow).where(IndentureRow.community_entity_id == node_id).order_by(IndentureRow.id)))
        manumissions = list(
            await session.scalars(select(ManumissionRow).where(ManumissionRow.community_entity_id == node_id).order_by(ManumissionRow.id.desc()))
        )
        kinship = await session.get(KinshipSystemRow, node_id)
        union = await session.get(UnionCustomRow, node_id)
        reproduction = await session.get(PeopleReproductionRow, node_id)
        caste = await session.get(MortalCasteRow, node_id)
        market = await session.get(SlaveMarketRow, node_id)
        refs = await refs_of(
            session,
            [
                node_id,
                *(row.source_node_id for row in challenges),
                *(ref for row in plans for ref in (row.holder_node_id, row.author_node_id, row.carrier_node_id, row.target_node_id)),
                *(ref for row in gifts for ref in (row.giver_node_id, row.receiver_node_id, row.item_entity_id)),
                *(ref for row in debts for ref in (row.god_node_id, row.community_entity_id)),
                *(ref for row in circuits for ref in (row.item_entity_id, *row.stops)),
                *(ref for row in alliances for ref in (row.giver_entity_id, row.taker_entity_id, row.treaty_id)),
                *(camp.circuit if camp is not None else []),
                *(ref for row in confederations for ref in (row.leader_entity_id, *row.members)),
                *(row.predecessor_entity_id for row in legacies),
                *(int(row.key) for row in legacies if row.kind in NAMED_LEGACIES and row.key.isdigit()),
                *(ref for row in indentures for ref in (row.employer_node_id, row.origin_entity_id)),
                *(row.origin_entity_id for row in manumissions),
            ],
        )
        return CyclesView(
            node=own[node_id],
            stress=stress_view(stress) if stress is not None else None,
            readings=[reading_view(row) for row in readings],
            solidarity=SolidarityView(
                value=solidarity.value,
                frontier=solidarity.frontier,
                luxury_generations=solidarity.luxury_generations,
                conflict=solidarity.conflict,
                updated_epoch=solidarity.updated_epoch,
                locked=list(solidarity.locked),
            )
            if solidarity is not None
            else None,
            challenges=[
                ChallengeView(id=row.id, kind=row.kind, severity=row.severity, response=row.response, source=at(refs, row.source_node_id), epoch=row.epoch)
                for row in challenges
            ],
            plans=[plan_view(row, refs) for row in plans],
            gifts=[gift_view(row, refs) for row in gifts],
            gift_balance=balance(gifts, node_id),
            debts=[
                OfferingLedgerView(
                    god=need(refs, row.god_node_id),
                    community=need(refs, row.community_entity_id),
                    offered=row.offered,
                    answered=row.answered,
                    last_offering_epoch=row.last_offering_epoch,
                    last_answer_epoch=row.last_answer_epoch,
                    locked=list(row.locked),
                )
                for row in debts
            ],
            circuits=[circuit_view(row, refs) for row in circuits],
            kinship=KinshipView(
                descent=kinship.descent,
                residence=kinship.residence,
                descent_group=kinship.descent_group,
                cousin_terms=kinship.cousin_terms,
                preference=kinship.preference,
                payment=kinship.payment,
                payment_value=kinship.payment_value,
                levirate=kinship.levirate,
                sororate=kinship.sororate,
                locked=list(kinship.locked),
            )
            if kinship is not None
            else None,
            union=UnionView(
                form=union.form,
                purpose=union.purpose,
                residence=union.residence,
                descent=union.descent,
                exchange=union.exchange,
                arrangement=union.arrangement,
                dissolution=union.dissolution,
                endogamy=union.endogamy,
                exogamy=union.exogamy,
                term_epochs=union.term_epochs,
                locked=list(union.locked),
            )
            if union is not None
            else None,
            alliances=[
                AllianceView(
                    giver=need(refs, row.giver_entity_id),
                    taker=need(refs, row.taker_entity_id),
                    marriages=row.marriages,
                    treaty=at(refs, row.treaty_id),
                    since_epoch=row.since_epoch,
                    last_epoch=row.last_epoch,
                    locked=list(row.locked),
                )
                for row in alliances
            ],
            reproduction=ReproductionView(
                system=reproduction.system,
                change_age=reproduction.change_age,
                breeder_pct=reproduction.breeder_pct,
                soldier_pct=reproduction.soldier_pct,
                worker_pct=reproduction.worker_pct,
                locked=list(reproduction.locked),
            )
            if reproduction is not None
            else None,
            caste=CasteView(caste=caste.caste, since_epoch=caste.since_epoch, locked=list(caste.locked)) if caste is not None else None,
            camp=CampView(
                mode=camp.mode,
                circuit=[refs[region] for region in camp.circuit if region in refs],
                season_index=camp.season_index,
                herd=camp.herd,
                grazing=camp.grazing,
                water=camp.water,
                last_moved_epoch=camp.last_moved_epoch,
                locked=list(camp.locked),
            )
            if camp is not None
            else None,
            confederations=[confederation_view(row, refs) for row in confederations],
            legacies=[
                LegacyView(
                    kind=row.kind,
                    key=row.key,
                    key_label=legacy_label(row, refs),
                    predecessor=at(refs, row.predecessor_entity_id),
                    since_epoch=row.since_epoch,
                    locked=list(row.locked),
                )
                for row in legacies
            ],
            indentures=[
                IndentureView(
                    id=row.id,
                    employer=at(refs, row.employer_node_id),
                    regime=row.regime,
                    count=row.count,
                    term_epochs=row.term_epochs,
                    debt=row.debt,
                    exploitation=row.exploitation,
                    origin=at(refs, row.origin_entity_id),
                    since_epoch=row.since_epoch,
                    locked=list(row.locked),
                )
                for row in indentures
            ],
            market=BondMarketView(
                price=market.price, stock=market.stock, sold=market.sold, open=market.open, updated_epoch=market.updated_epoch, locked=list(market.locked)
            )
            if market is not None
            else None,
            manumissions=[
                ManumissionView(
                    id=row.id,
                    count=row.count,
                    path=row.path,
                    standing=row.standing,
                    origin=at(refs, row.origin_entity_id),
                    epoch=row.epoch,
                    locked=list(row.locked),
                )
                for row in manumissions
            ],
        )


async def frontier_views(session: AsyncSession) -> list[FrontierView]:
    atlas = await RegionAtlas.load(session)
    rows = list(await session.scalars(select(AsabiyyaRow).order_by(AsabiyyaRow.value.desc(), AsabiyyaRow.holder_entity_id)))
    regions: dict[int, list[int]] = {}
    for row in rows:
        holder = await session.get(EntityRow, row.holder_entity_id)
        homes = await homes_of(session, holder) if holder is not None else set()
        regions[row.holder_entity_id] = sorted({region for home in homes if (region := atlas.top_region(home)) is not None})
    refs = await refs_of(session, [*(row.holder_entity_id for row in rows), *(region for found in regions.values() for region in found)])
    return [
        FrontierView(
            holder=refs[row.holder_entity_id],
            value=row.value,
            frontier=row.frontier,
            conflict=row.conflict,
            regions=[refs[region] for region in regions[row.holder_entity_id] if region in refs],
        )
        for row in rows
        if row.holder_entity_id in refs
    ]


@router.get("/cycles/cosmos", response_model=CosmosCyclesView)
async def cosmos_cycles(services: ServicesDep) -> CosmosCyclesView:
    async with reader(services) as session:
        stresses = list(await session.scalars(select(PolityStressRow).order_by(PolityStressRow.psi.desc(), PolityStressRow.polity_entity_id)))
        readings: dict[int, list[StressReadingRow]] = {}
        for row in await session.scalars(select(StressReadingRow).order_by(StressReadingRow.polity_entity_id, StressReadingRow.epoch)):
            readings.setdefault(row.polity_entity_id, []).append(row)
        circuits = await circuits_of(session, None)
        confederations = await confederations_of(session, None)
        plans = await plans_of(session, None)
        gifts = await gifts_of(session, None)
        refs = await refs_of(
            session,
            [
                *(row.polity_entity_id for row in stresses),
                *(ref for row in circuits for ref in (row.item_entity_id, *row.stops)),
                *(ref for row in confederations for ref in (row.leader_entity_id, *row.members)),
                *(ref for row in plans for ref in (row.holder_node_id, row.author_node_id, row.carrier_node_id, row.target_node_id)),
                *(ref for row in gifts for ref in (row.giver_node_id, row.receiver_node_id, row.item_entity_id)),
            ],
        )
        return CosmosCyclesView(
            realms=[
                RealmCycleView(
                    polity=refs[row.polity_entity_id],
                    psi=row.psi,
                    phase=row.phase,
                    challenge=row.challenge,
                    readings=[reading_view(item) for item in readings.get(row.polity_entity_id, [])],
                )
                for row in stresses
                if row.polity_entity_id in refs
            ],
            frontiers=await frontier_views(session),
            circuits=[circuit_view(row, refs) for row in circuits],
            confederations=[confederation_view(row, refs) for row in confederations],
            plans=[plan_view(row, refs) for row in plans if row.holder_node_id in refs],
            gifts=[gift_view(row, refs) for row in gifts if row.giver_node_id in refs and row.receiver_node_id in refs],
        )
