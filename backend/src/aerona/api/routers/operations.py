from collections.abc import Iterable
from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.operations import (
    AdmiraltyView,
    CrewView,
    DepotView,
    EchelonView,
    ExpeditionLogView,
    ExpeditionMemberView,
    ExpeditionView,
    OperationsNodeView,
    OperationView,
    QuirkView,
    ShipSectionView,
    ShipView,
    StackPlacementView,
    SupplyFlowView,
    TheatreView,
    TransportView,
    WarOptionView,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.catalog.operations import ROLE_CAPACITY
from aerona.core.errors import NotFoundError
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.military import ArmyUnitRow
from aerona.db.tables.operations import (
    AdmiraltyRow,
    ArmyOperationRow,
    DepotRow,
    EchelonRow,
    ExpeditionLogRow,
    ExpeditionMemberRow,
    ExpeditionRow,
    QuirkRow,
    ShipCrewRow,
    ShipStateRow,
    SupplyFlowRow,
    TheatreRow,
    TransportAssetRow,
)
from aerona.db.tables.vehicles import VesselSectionRow
from aerona.db.tables.warfare import WarRow
from aerona.domain.enums.node import NodeKind
from aerona.engine.operations.crews import fitted_stations
from aerona.engine.services.war import ongoing_wars

router = APIRouter(tags=["operations"])
NodeId = Annotated[int, Path(ge=1)]


def at(refs: dict[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


def ref(refs: dict[int, NodeRef], node_id: int) -> NodeRef:
    return refs[node_id] if node_id in refs else NodeRef(id=node_id, kind=NodeKind.ENTITY, name="a lost record")


async def refs_of(session: AsyncSession, ids: Iterable[int | None]) -> dict[int, NodeRef]:
    return await node_refs(session, sorted({value for value in ids if value is not None}))


def echelon_view(row: EchelonRow, refs: dict[int, NodeRef], stacks: int) -> EchelonView:
    return EchelonView(
        id=row.id,
        owner=ref(refs, row.owner_entity_id),
        army=at(refs, row.army_entity_id),
        parent_id=row.parent_id,
        level=row.level,
        name=row.name,
        commander=at(refs, row.commander_entity_id),
        hq=at(refs, row.hq_region_entity_id),
        staff=row.staff,
        command_range=row.command_range,
        command_points=row.command_points,
        points_spent=row.points_spent,
        order=row.order,
        in_range=row.in_range,
        formed_epoch=row.formed_epoch,
        stacks=stacks,
        locked=row.locked,
    )


def flow_view(row: SupplyFlowRow, refs: dict[int, NodeRef]) -> SupplyFlowView:
    return SupplyFlowView(
        id=row.id,
        epoch=row.epoch,
        season=row.season,
        owner=ref(refs, row.owner_entity_id),
        army=ref(refs, row.army_entity_id),
        depot_id=row.depot_id,
        produced=row.produced,
        shipped=row.shipped,
        lost=row.lost,
        delivered=row.delivered,
        need=row.need,
        throughput=row.throughput,
        locked=row.locked,
    )


def depot_view(row: DepotRow, refs: dict[int, NodeRef]) -> DepotView:
    return DepotView(
        id=row.id,
        owner=ref(refs, row.owner_entity_id),
        region=at(refs, row.region_entity_id),
        structure=at(refs, row.structure_entity_id),
        supplies=row.supplies,
        capacity=row.capacity,
        field=row.field,
        cut=row.cut,
        founded_epoch=row.founded_epoch,
        locked=row.locked,
    )


def transport_view(row: TransportAssetRow, refs: dict[int, NodeRef]) -> TransportView:
    return TransportView(
        id=row.id,
        owner=ref(refs, row.owner_entity_id),
        depot_id=row.depot_id,
        transport_kind=row.kind,
        count=row.count,
        capacity=row.capacity,
        condition=row.condition,
        locked=row.locked,
    )


def theatre_view(row: TheatreRow, refs: dict[int, NodeRef], events: dict[int, int]) -> TheatreView:
    return TheatreView(
        id=row.id,
        owner=ref(refs, row.owner_entity_id),
        war_id=row.war_id,
        war=at(refs, events.get(row.war_id)),
        front=at(refs, row.front_region_entity_id),
        marshal=at(refs, row.marshal_entity_id),
        priority=row.priority,
        believed_threat=row.believed_threat,
        true_threat=row.true_threat,
        reserves=row.reserves,
        levies=row.levies,
        transport=row.transport,
        misjudged=row.misjudged,
        updated_epoch=row.updated_epoch,
        locked=row.locked,
    )


def operation_view(row: ArmyOperationRow, refs: dict[int, NodeRef]) -> OperationView:
    return OperationView(
        army=ref(refs, row.army_entity_id),
        offensive_seasons=row.offensive_seasons,
        need=row.need,
        delivered=row.delivered,
        organisation=row.organisation,
        culminated=row.culminated,
        culminated_epoch=row.culminated_epoch,
        pause_seasons=row.pause_seasons,
        foresight=row.foresight,
        standing=row.standing,
        updated_epoch=row.updated_epoch,
        locked=row.locked,
    )


def admiralty_view(row: AdmiraltyRow, refs: dict[int, NodeRef]) -> AdmiraltyView:
    return AdmiraltyView(
        polity=ref(refs, row.polity_entity_id),
        admiral=at(refs, row.admiral_entity_id),
        budget_share=row.budget_share,
        requested=row.requested,
        influence=row.influence,
        tonnage=row.tonnage,
        limit_tonnage=row.limit_tonnage,
        concealed=row.concealed,
        commissioned=row.commissioned,
        updated_epoch=row.updated_epoch,
        locked=row.locked,
    )


def ship_view(row: ShipStateRow, vessel: VesselProfileRow | None, sections: list[VesselSectionRow], refs: dict[int, NodeRef]) -> ShipView:
    return ShipView(
        vessel=ref(refs, row.vessel_entity_id),
        heading=row.heading,
        wind_from=row.wind_from,
        point_of_sail=row.point_of_sail,
        tacks=row.tacks,
        shot=row.shot,
        leak=row.leak,
        fire=row.fire,
        magazine=row.magazine,
        rate_of_fire=row.rate_of_fire,
        rower_fatigue=row.rower_fatigue,
        raked=row.raked,
        struck=row.struck,
        prize_of=at(refs, row.prize_of_entity_id),
        prize_crew=row.prize_crew,
        prize_money=row.prize_money,
        hull_condition=vessel.condition if vessel is not None else 0,
        crew_total=vessel.crew if vessel is not None else 0,
        sections=[ShipSectionView(section=item.section, state=item.state, condition=item.condition) for item in sections],
        updated_epoch=row.updated_epoch,
        locked=row.locked,
    )


def quirk_view(row: QuirkRow, refs: dict[int, NodeRef]) -> QuirkView:
    return QuirkView(
        id=row.id,
        quirk_kind=row.kind,
        source=at(refs, row.source_entity_id),
        expedition_id=row.expedition_id,
        strength=row.strength,
        gained_epoch=row.gained_epoch,
        locked=row.locked,
    )


def member_view(row: ExpeditionMemberRow, refs: dict[int, NodeRef]) -> ExpeditionMemberView:
    return ExpeditionMemberView(
        id=row.id,
        mortal=ref(refs, row.mortal_entity_id),
        role=row.role,
        stress=row.stress,
        resolve=row.resolve,
        cold=row.cold,
        wet=row.wet,
        hunger=row.hunger,
        fatigue=row.fatigue,
        fallen=row.fallen,
        locked=row.locked,
    )


def log_view(row: ExpeditionLogRow, refs: dict[int, NodeRef]) -> ExpeditionLogView:
    return ExpeditionLogView(
        id=row.id,
        epoch=row.epoch,
        leg=row.leg,
        event=row.event,
        member=at(refs, row.member_entity_id),
        provisions_used=row.provisions_used,
        light_used=row.light_used,
        stress=row.stress,
        resolve=row.resolve,
        quirk=row.quirk,
        locked=row.locked,
    )


def expedition_view(row: ExpeditionRow, members: list[ExpeditionMemberRow], log: list[ExpeditionLogRow], refs: dict[int, NodeRef]) -> ExpeditionView:
    held = {member.role for member in members if not member.fallen}
    return ExpeditionView(
        id=row.id,
        name=row.name,
        leader=at(refs, row.leader_entity_id),
        sponsor=at(refs, row.sponsor_node_id),
        target=at(refs, row.target_entity_id),
        ground=row.ground,
        status=row.status,
        legs_done=row.legs_done,
        legs_total=row.legs_total,
        provisions=row.provisions,
        light=row.light,
        tools=row.tools,
        medicine=row.medicine,
        darkness=row.darkness,
        danger=row.danger,
        found=row.found,
        started_epoch=row.started_epoch,
        ended_epoch=row.ended_epoch,
        missing_roles=[role for role in ROLE_CAPACITY if role not in held],
        members=[member_view(member, refs) for member in members],
        log=[log_view(entry, refs) for entry in log],
        locked=row.locked,
    )


async def expeditions_of(session: AsyncSession, node_id: int) -> list[ExpeditionRow]:
    member_of = select(ExpeditionMemberRow.expedition_id).where(ExpeditionMemberRow.mortal_entity_id == node_id)
    rows = await session.scalars(
        select(ExpeditionRow)
        .where(
            or_(
                ExpeditionRow.leader_entity_id == node_id,
                ExpeditionRow.target_entity_id == node_id,
                ExpeditionRow.sponsor_node_id == node_id,
                ExpeditionRow.id.in_(member_of),
            )
        )
        .order_by(ExpeditionRow.id.desc())
    )
    return list(rows)


@router.get("/operations/of/{node_id}", response_model=OperationsNodeView)
async def node_operations(services: ServicesDep, node_id: NodeId) -> OperationsNodeView:
    async with reader(services) as session:
        own = await node_refs(session, [node_id])
        if node_id not in own:
            raise NotFoundError("No such thing.")
        echelons = list(
            await session.scalars(
                select(EchelonRow).where(or_(EchelonRow.army_entity_id == node_id, EchelonRow.owner_entity_id == node_id)).order_by(EchelonRow.id)
            )
        )
        stacks = list(await session.scalars(select(ArmyUnitRow).where(ArmyUnitRow.army_entity_id == node_id).order_by(ArmyUnitRow.id)))
        counted = {row.id: 0 for row in echelons}
        for unit in await session.scalars(select(ArmyUnitRow).where(ArmyUnitRow.echelon_id.in_(list(counted) or [0]))):
            counted[unit.echelon_id or 0] = counted.get(unit.echelon_id or 0, 0) + 1
        operation = await session.get(ArmyOperationRow, node_id)
        flows = list(
            await session.scalars(
                select(SupplyFlowRow)
                .where(or_(SupplyFlowRow.army_entity_id == node_id, SupplyFlowRow.owner_entity_id == node_id))
                .order_by(SupplyFlowRow.epoch.desc(), SupplyFlowRow.season.desc(), SupplyFlowRow.id.desc())
            )
        )
        depots = list(
            await session.scalars(select(DepotRow).where(or_(DepotRow.owner_entity_id == node_id, DepotRow.region_entity_id == node_id)).order_by(DepotRow.id))
        )
        transport = list(await session.scalars(select(TransportAssetRow).where(TransportAssetRow.owner_entity_id == node_id).order_by(TransportAssetRow.id)))
        theatres = list(await session.scalars(select(TheatreRow).where(TheatreRow.owner_entity_id == node_id).order_by(TheatreRow.id)))
        wars = [item for item in await ongoing_wars(session, node_id)]
        events = {
            row.id: row.event_entity_id
            for row in await session.scalars(select(WarRow).where(WarRow.id.in_([row.war_id for row in theatres] + [item.war.id for item in wars] or [0])))
        }
        admiralty = await session.get(AdmiraltyRow, node_id)
        ship = await session.get(ShipStateRow, node_id)
        vessel = await session.get(VesselProfileRow, node_id)
        sections = list(await session.scalars(select(VesselSectionRow).where(VesselSectionRow.vessel_entity_id == node_id).order_by(VesselSectionRow.section)))
        crews = list(await session.scalars(select(ShipCrewRow).where(ShipCrewRow.vessel_entity_id == node_id).order_by(ShipCrewRow.station)))
        quirks = list(await session.scalars(select(QuirkRow).where(QuirkRow.mortal_entity_id == node_id).order_by(QuirkRow.id)))
        expeditions = await expeditions_of(session, node_id)
        ids = [row.id for row in expeditions] or [0]
        members = list(await session.scalars(select(ExpeditionMemberRow).where(ExpeditionMemberRow.expedition_id.in_(ids)).order_by(ExpeditionMemberRow.id)))
        logs = list(await session.scalars(select(ExpeditionLogRow).where(ExpeditionLogRow.expedition_id.in_(ids)).order_by(ExpeditionLogRow.id)))
        refs = await refs_of(
            session,
            [
                node_id,
                *(item for row in echelons for item in (row.owner_entity_id, row.army_entity_id, row.commander_entity_id, row.hq_region_entity_id)),
                *(item for row in flows for item in (row.owner_entity_id, row.army_entity_id)),
                *(item for row in depots for item in (row.owner_entity_id, row.region_entity_id, row.structure_entity_id)),
                *(row.owner_entity_id for row in transport),
                *(item for row in theatres for item in (row.owner_entity_id, row.front_region_entity_id, row.marshal_entity_id)),
                *events.values(),
                *(side for item in wars for side in item.sides),
                *((admiralty.polity_entity_id, admiralty.admiral_entity_id) if admiralty is not None else ()),
                *((ship.vessel_entity_id, ship.prize_of_entity_id) if ship is not None else ()),
                *(row.source_entity_id for row in quirks),
                *(item for row in expeditions for item in (row.leader_entity_id, row.sponsor_node_id, row.target_entity_id)),
                *(row.mortal_entity_id for row in members),
                *(row.member_entity_id for row in logs),
            ],
        )
        return OperationsNodeView(
            node=own[node_id],
            echelons=[echelon_view(row, refs, counted.get(row.id, 0)) for row in echelons],
            stacks=[StackPlacementView(id=row.id, unit_kind=row.kind, count=row.count, echelon_id=row.echelon_id, locked=row.locked) for row in stacks],
            operation=operation_view(operation, refs) if operation is not None else None,
            flows=[flow_view(row, refs) for row in flows],
            depots=[depot_view(row, refs) for row in depots],
            transport=[transport_view(row, refs) for row in transport],
            theatres=[theatre_view(row, refs, events) for row in theatres],
            wars=[
                WarOptionView(
                    war_id=item.war.id,
                    war=at(refs, events.get(item.war.id)),
                    enemy=ref(refs, item.foe_id),
                )
                for item in wars
            ],
            admiralty=admiralty_view(admiralty, refs) if admiralty is not None else None,
            ship=ship_view(ship, vessel, sections, refs) if ship is not None else None,
            crews=[CrewView(station=row.station, count=row.count, skill=row.skill, locked=row.locked) for row in crews],
            crew_stations=await fitted_stations(session, node_id, vessel) if vessel is not None else [],
            quirks=[quirk_view(row, refs) for row in quirks],
            expeditions=[
                expedition_view(row, [item for item in members if item.expedition_id == row.id], [item for item in logs if item.expedition_id == row.id], refs)
                for row in expeditions
            ],
        )
