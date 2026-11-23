from sqlalchemy import select

from aerona.catalog.operations import CREW_STATIONS, TRANSPORTS
from aerona.core.errors import ValidationFailedError
from aerona.db.base import Base
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyUnitRow
from aerona.db.tables.operations import (
    ADMIRALTY_FIELDS,
    CREW_FIELDS,
    DEPOT_FIELDS,
    ECHELON_FIELDS,
    EXPEDITION_FIELDS,
    FLOW_FIELDS,
    LOG_FIELDS,
    MEMBER_FIELDS,
    OPERATION_FIELDS,
    QUIRK_FIELDS,
    SHIP_FIELDS,
    THEATRE_FIELDS,
    TRANSPORT_FIELDS,
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
from aerona.db.tables.warfare import WarRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import MovementMode
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.operations import CarrierKind, CrewStation, EchelonLevel, ExpeditionEvent, ExpeditionRole, ExpeditionStatus, QuirkKind
from aerona.engine.collective.control import of_type, saved
from aerona.engine.context import TickContext
from aerona.engine.cycles.control import node_exists, put_values
from aerona.engine.divine.control import apply
from aerona.engine.gatherings.control import Values, allowed, found
from aerona.engine.operations.crews import fitted_stations
from aerona.engine.operations.expeditions import ExpeditionTally, advance, grant_quirk, launch, party_of
from aerona.engine.operations.sail import ship_state
from aerona.engine.operations.supply import operation_of
from aerona.engine.operations.theatres import theatre_of
from aerona.engine.recording.record import record

OWNERS = frozenset({EntityType.POLITY, EntityType.SETTLEMENT, EntityType.PEOPLE, EntityType.FACTION, EntityType.HOUSE})
ARMIES = frozenset({EntityType.ARMY})
REGIONS = frozenset({EntityType.REGION})
MORTALS = frozenset({EntityType.MORTAL})
POLITIES = frozenset({EntityType.POLITY})
VESSELS = frozenset({EntityType.VESSEL})
NAME = 200


async def form_echelon(
    ctx: TickContext, owner_id: int, level: EchelonLevel, name: str, *, army_id: int | None, parent_id: int | None, commander_id: int | None
) -> EchelonRow:
    await of_type(ctx, owner_id, OWNERS, "a realm or a people")
    if army_id is not None:
        await of_type(ctx, army_id, ARMIES, "an army")
    if parent_id is not None:
        await found(ctx, EchelonRow, parent_id, "formation")
    if commander_id is not None:
        await of_type(ctx, commander_id, MORTALS, "a mortal")
    row = await saved(
        ctx,
        EchelonRow(
            owner_entity_id=owner_id,
            army_entity_id=army_id,
            level=level,
            name=name[:NAME],
            parent_id=parent_id,
            commander_entity_id=commander_id,
            formed_epoch=ctx.epoch,
            locked=[],
        ),
    )
    apply(row, {key: getattr(row, key) for key in ("parent_id", "commander_entity_id")}, [])
    await ctx.session.flush()
    return row


async def assign_stack(ctx: TickContext, stack_id: int, echelon_id: int | None) -> ArmyUnitRow:
    stack = await found(ctx, ArmyUnitRow, stack_id, "stack")
    if echelon_id is not None:
        echelon = await found(ctx, EchelonRow, echelon_id, "formation")
        if echelon.army_entity_id not in {None, stack.army_entity_id}:
            raise ValidationFailedError("That formation belongs to another army.")
    apply(stack, {"echelon_id": echelon_id}, [])
    await ctx.session.flush()
    return stack


async def found_depot(ctx: TickContext, owner_id: int, region_id: int, *, field: bool, capacity: int, supplies: int) -> DepotRow:
    owner = await of_type(ctx, owner_id, OWNERS, "a realm or a people")
    region = await of_type(ctx, region_id, REGIONS, "a land")
    row = await saved(
        ctx,
        DepotRow(
            owner_entity_id=owner_id,
            region_entity_id=region_id,
            field=field,
            capacity=capacity,
            supplies=min(supplies, capacity),
            founded_epoch=ctx.epoch,
            locked=[],
        ),
    )
    await record(
        ctx,
        "logistics.depot_founded",
        roles={IncidentRole.ACTOR: owner.id},
        facts={"region": region.id, "supplies": row.supplies, "capacity": row.capacity},
        place=region.id,
    )
    return row


async def add_transport(ctx: TickContext, owner_id: int, kind: CarrierKind, count: int, depot_id: int | None) -> TransportAssetRow:
    await of_type(ctx, owner_id, OWNERS, "a realm or a people")
    if depot_id is not None:
        await found(ctx, DepotRow, depot_id, "depot")
    row = await ctx.session.scalar(select(TransportAssetRow).where(TransportAssetRow.owner_entity_id == owner_id, TransportAssetRow.kind == kind))
    if row is None:
        row = await saved(ctx, TransportAssetRow(owner_entity_id=owner_id, kind=kind, capacity=TRANSPORTS[kind].capacity, locked=[]))
    return await put_values(ctx, row, {"count": row.count + count, "depot_id": depot_id}, TRANSPORT_FIELDS, "transport")


async def set_operation(ctx: TickContext, army_id: int, values: Values) -> ArmyOperationRow:
    await of_type(ctx, army_id, ARMIES, "an army")
    return await put_values(ctx, await operation_of(ctx, army_id), values, OPERATION_FIELDS, "operation")


async def open_theatre(ctx: TickContext, owner_id: int, war_id: int, values: Values) -> TheatreRow:
    await of_type(ctx, owner_id, OWNERS, "a realm or a people")
    await found(ctx, WarRow, war_id, "war")
    return await put_values(ctx, await theatre_of(ctx, owner_id, war_id), values, THEATRE_FIELDS, "theatre")


async def set_ship(ctx: TickContext, vessel_id: int, values: Values) -> ShipStateRow:
    await of_type(ctx, vessel_id, VESSELS, "a vessel")
    await found(ctx, VesselProfileRow, vessel_id, "ship")
    return await put_values(ctx, await ship_state(ctx, vessel_id), values, SHIP_FIELDS, "ship's state")


async def set_crew(ctx: TickContext, vessel_id: int, station: CrewStation, values: Values) -> ShipCrewRow:
    await of_type(ctx, vessel_id, VESSELS, "a vessel")
    vessel = await ctx.session.get(VesselProfileRow, vessel_id)
    if vessel is not None and station not in await fitted_stations(ctx.session, vessel_id, vessel):
        raise ValidationFailedError(f"No section of this vessel calls for {CREW_STATIONS[station].label.lower()}.")
    row = await ctx.session.get(ShipCrewRow, (vessel_id, station)) or await saved(ctx, ShipCrewRow(vessel_entity_id=vessel_id, station=station, locked=[]))
    row = await put_values(ctx, row, values, CREW_FIELDS, "crew station")
    await muster_crew(ctx, vessel_id)
    return row


async def muster_crew(ctx: TickContext, vessel_id: int) -> None:
    vessel = await ctx.session.get(VesselProfileRow, vessel_id)
    if vessel is None or "crew" in vessel.locked:
        return
    vessel.crew = sum(item.count for item in await ctx.session.scalars(select(ShipCrewRow).where(ShipCrewRow.vessel_entity_id == vessel_id)))
    await ctx.session.flush()


async def set_admiralty(ctx: TickContext, polity_id: int, values: Values) -> AdmiraltyRow:
    await of_type(ctx, polity_id, POLITIES, "a realm")
    row = await ctx.session.get(AdmiraltyRow, polity_id) or await saved(ctx, AdmiraltyRow(polity_entity_id=polity_id, updated_epoch=ctx.epoch, locked=[]))
    return await put_values(ctx, row, values, ADMIRALTY_FIELDS, "admiralty")


async def send_expedition(
    ctx: TickContext,
    leader_id: int,
    target_id: int,
    companion_ids: list[int],
    sponsor_id: int | None,
    *,
    mode: MovementMode | None = None,
    carried: bool = False,
) -> ExpeditionRow:
    leader = await of_type(ctx, leader_id, MORTALS, "a mortal")
    target: EntityRow = await found(ctx, EntityRow, target_id, "destination")
    companions = [await of_type(ctx, item, MORTALS, "a mortal") for item in dict.fromkeys(companion_ids) if item != leader_id]
    if sponsor_id is not None:
        await node_exists(ctx, sponsor_id, "sponsor")
    return await launch(ctx, leader, target, companions, sponsor_id=sponsor_id, tally=ExpeditionTally(), mode=mode, carried=carried)


async def press_on(ctx: TickContext, expedition_id: int, legs: int) -> ExpeditionRow:
    row = await found(ctx, ExpeditionRow, expedition_id, "expedition")
    if row.status in {ExpeditionStatus.RETURNED, ExpeditionStatus.LOST}:
        raise ValidationFailedError("That expedition is over.")
    await advance(ctx, row, ExpeditionTally(), legs)
    await ctx.session.flush()
    return row


async def recall(ctx: TickContext, expedition_id: int) -> ExpeditionRow:
    row = await found(ctx, ExpeditionRow, expedition_id, "expedition")
    if row.status in {ExpeditionStatus.RETURNED, ExpeditionStatus.LOST}:
        raise ValidationFailedError("That expedition is over.")
    party = await party_of(ctx, row)
    apply(row, {"status": ExpeditionStatus.RETURNED if party.alive else ExpeditionStatus.LOST}, [])
    row.ended_epoch = ctx.epoch
    ctx.session.add(ExpeditionLogRow(expedition_id=row.id, epoch=ctx.epoch, leg=row.legs_done, event=ExpeditionEvent.RETURN, locked=[]))
    await ctx.session.flush()
    return row


async def add_member(ctx: TickContext, expedition_id: int, mortal_id: int, role: ExpeditionRole) -> ExpeditionMemberRow:
    await found(ctx, ExpeditionRow, expedition_id, "expedition")
    await of_type(ctx, mortal_id, MORTALS, "a mortal")
    existing = await ctx.session.scalar(
        select(ExpeditionMemberRow.id).where(ExpeditionMemberRow.expedition_id == expedition_id, ExpeditionMemberRow.mortal_entity_id == mortal_id)
    )
    if existing is not None:
        raise ValidationFailedError("That mortal is already in the party.")
    return await saved(ctx, ExpeditionMemberRow(expedition_id=expedition_id, mortal_entity_id=mortal_id, role=role, locked=[]))


async def give_quirk(ctx: TickContext, mortal_id: int, kind: QuirkKind, source_id: int | None) -> QuirkRow:
    await of_type(ctx, mortal_id, MORTALS, "a mortal")
    if source_id is not None:
        await found(ctx, EntityRow, source_id, "place or event")
    row = await grant_quirk(ctx, mortal_id, kind, source_id=source_id, expedition_id=None)
    await ctx.session.flush()
    return row


EDITABLE: dict[str, tuple[type[Base], tuple[str, ...], str]] = {
    "echelon": (EchelonRow, ECHELON_FIELDS, "formation"),
    "depot": (DepotRow, DEPOT_FIELDS, "depot"),
    "transport": (TransportAssetRow, TRANSPORT_FIELDS, "transport"),
    "supply_flow": (SupplyFlowRow, FLOW_FIELDS, "supply flow"),
    "army_operation": (ArmyOperationRow, OPERATION_FIELDS, "operation"),
    "theatre": (TheatreRow, THEATRE_FIELDS, "theatre"),
    "ship_state": (ShipStateRow, SHIP_FIELDS, "ship's state"),
    "ship_crew": (ShipCrewRow, CREW_FIELDS, "crew station"),
    "admiralty": (AdmiraltyRow, ADMIRALTY_FIELDS, "admiralty"),
    "expedition": (ExpeditionRow, EXPEDITION_FIELDS, "expedition"),
    "expedition_member": (ExpeditionMemberRow, MEMBER_FIELDS, "member"),
    "expedition_log": (ExpeditionLogRow, LOG_FIELDS, "log entry"),
    "quirk": (QuirkRow, QUIRK_FIELDS, "quirk"),
}


async def edit_record(ctx: TickContext, kind: str, key: object, values: Values, release: list[str]) -> Base:
    table, fields, label = EDITABLE[kind]
    row = apply(await found(ctx, table, key, label), allowed(values, fields, label), release)
    await ctx.session.flush()
    if isinstance(row, ShipCrewRow):
        await muster_crew(ctx, row.vessel_entity_id)
    return row


async def delete_record(ctx: TickContext, kind: str, key: object) -> None:
    table, _, label = EDITABLE[kind]
    await ctx.session.delete(await found(ctx, table, key, label))
    await ctx.session.flush()
