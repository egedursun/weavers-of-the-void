from sqlalchemy import select

from aerona.agents.context.cycle_lines import named, words
from aerona.agents.context.scope import Scope
from aerona.catalog.operations import GROUND_LABELS, QUIRKS, RESOLVE_EFFECTS
from aerona.core.grammar import an, several
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.operations import (
    AdmiraltyRow,
    ArmyOperationRow,
    DepotRow,
    EchelonRow,
    ExpeditionMemberRow,
    ExpeditionRow,
    QuirkRow,
    ShipStateRow,
    TheatreRow,
)
from aerona.db.tables.polity import OfficeRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.warfare import ArmyRow
from aerona.domain.enums.operations import EchelonLevel, EchelonOrder, ExpeditionStatus
from aerona.domain.enums.polity import OfficeKind

LIST_LINES = 3
UNDER_WAY = (ExpeditionStatus.UNDERWAY, ExpeditionStatus.CAMPED)
WAR_OFFICES = (OfficeKind.RULER, OfficeKind.MARSHAL, OfficeKind.ADMIRAL)


async def quirk_lines(scope: Scope, me: EntityRow) -> list[str]:
    rows = list(await scope.session.scalars(select(QuirkRow).where(QuirkRow.mortal_entity_id == me.id).order_by(QuirkRow.id)))
    if not rows:
        return []
    return ["your quirks: " + "; ".join(f"{QUIRKS[row.kind].label.lower()} ({QUIRKS[row.kind].effect}, strength {row.strength})" for row in rows)]


async def expedition_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    for member, row in await session.execute(
        select(ExpeditionMemberRow, ExpeditionRow)
        .join(ExpeditionRow, ExpeditionRow.id == ExpeditionMemberRow.expedition_id)
        .where(ExpeditionMemberRow.mortal_entity_id == me.id, ExpeditionRow.status.in_(UNDER_WAY))
        .limit(1)
    ):
        target = await named(scope, row.target_entity_id)
        found.append(
            f"you travel with {row.name} (expedition {row.id}) into {GROUND_LABELS[row.ground]}, {target}: leg {row.legs_done} of {row.legs_total}, "
            f"provisions {row.provisions}, light {row.light}, darkness {row.darkness}, medicine {row.medicine}"
        )
        found.append(
            f"you go as its {member.role.value}; stress {member.stress}, you {RESOLVE_EFFECTS[member.resolve]} ({member.resolve.value}); "
            f"cold {member.cold}, wet {member.wet}, hunger {member.hunger}, fatigue {member.fatigue}"
        )
    return found


async def command_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    for army_row in await session.scalars(
        select(ArmyRow).where(ArmyRow.commander_entity_id == me.id, ArmyRow.disbanded_epoch.is_(None)).order_by(ArmyRow.entity_id).limit(LIST_LINES)
    ):
        echelons = list(await session.scalars(select(EchelonRow).where(EchelonRow.army_entity_id == army_row.entity_id).order_by(EchelonRow.id)))
        brigades = [row for row in echelons if row.level is EchelonLevel.BRIGADE]
        standing = sum(1 for row in brigades if row.order is EchelonOrder.STANDING)
        top = next((row for row in echelons if row.level is EchelonLevel.ARMY), None)
        name = await named(scope, army_row.entity_id)
        head = f"your army {name} has {several(len(brigades), 'brigade', 'brigades')}, {standing} on standing orders"
        if top is not None:
            head += f"; your headquarters (formation {top.id}) has {top.command_points - top.points_spent} of {top.command_points} command points left"
        found.append(head)
        operation = await session.get(ArmyOperationRow, army_row.entity_id)
        if operation is not None and operation.need > 0:
            state = "its offensive has culminated" if operation.culminated else f"{operation.offensive_seasons} seasons on the offensive"
            found.append(f"it needs {operation.need} supply a season and received {operation.delivered}; {state}")
    for row in await session.scalars(select(EchelonRow).where(EchelonRow.commander_entity_id == me.id).order_by(EchelonRow.id).limit(LIST_LINES)):
        found.append(f"you command {row.name} (formation {row.id}), {an(words(row.level.value))} on {row.order.value} orders")
    return found


async def realm_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    offices = list(await session.scalars(select(OfficeRow).where(OfficeRow.holder_entity_id == me.id, OfficeRow.kind.in_(WAR_OFFICES)).order_by(OfficeRow.id)))
    for office in offices[:1]:
        realm = office.polity_entity_id
        for theatre in await session.scalars(select(TheatreRow).where(TheatreRow.owner_entity_id == realm).order_by(TheatreRow.id).limit(LIST_LINES)):
            found.append(
                f"theatre {theatre.id} of your realm faces {await named(scope, theatre.front_region_entity_id)}: priority {theatre.priority}, "
                f"believed threat {theatre.believed_threat}, reserves {theatre.reserves}, levies {theatre.levies}"
            )
        depots = list(await session.scalars(select(DepotRow).where(DepotRow.owner_entity_id == realm)))
        if depots:
            found.append(f"your realm keeps {several(len(depots), 'depot', 'depots')} holding {sum(row.supplies for row in depots)} supplies")
        admiralty = await session.get(AdmiraltyRow, realm)
        if admiralty is not None:
            cap = f" under a treaty limit of {admiralty.limit_tonnage}" if admiralty.limit_tonnage is not None else ""
            found.append(f"its admiralty holds {admiralty.budget_share}% of the war budget and a fleet of {admiralty.tonnage} tons{cap}")
    return found


async def ship_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    for vessel, state in await session.execute(
        select(VesselProfileRow, ShipStateRow)
        .join(ShipStateRow, ShipStateRow.vessel_entity_id == VesselProfileRow.entity_id)
        .where(VesselProfileRow.captain_entity_id == me.id)
        .limit(1)
    ):
        found.append(
            f"your ship {await named(scope, vessel.entity_id)} sails {words(state.point_of_sail.value)}, leaks {state.leak}, burns {state.fire}, "
            f"fires {state.shot.value} shot at a rate of {state.rate_of_fire}"
        )
    return found


async def mortal_operations_lines(scope: Scope, me: EntityRow) -> list[str]:
    return [
        *await quirk_lines(scope, me),
        *await expedition_lines(scope, me),
        *await command_lines(scope, me),
        *await realm_lines(scope, me),
        *await ship_lines(scope, me),
    ]


async def son_operations_lines(scope: Scope, son: SonRow) -> list[str]:
    if son.current_world_id is None:
        return []
    session = scope.session
    world = son.current_world_id
    found: list[str] = []
    for row, leader in await session.execute(
        select(ExpeditionRow, EntityRow)
        .join(EntityRow, EntityRow.id == ExpeditionRow.leader_entity_id)
        .where(EntityRow.world_id == world, ExpeditionRow.status.in_(UNDER_WAY))
        .order_by(ExpeditionRow.id)
        .limit(LIST_LINES)
    ):
        found.append(f"{leader.name} leads {row.name} (expedition {row.id}), leg {row.legs_done} of {row.legs_total}, provisions {row.provisions}")
    for theatre, owner in await session.execute(
        select(TheatreRow, EntityRow)
        .join(EntityRow, EntityRow.id == TheatreRow.owner_entity_id)
        .where(EntityRow.world_id == world)
        .order_by(TheatreRow.id)
        .limit(LIST_LINES)
    ):
        found.append(f"{owner.name} sends theatre {theatre.id} {theatre.priority} of every hundred of its reserves")
    for army in await session.scalars(
        select(EntityRow)
        .join(ArmyOperationRow, ArmyOperationRow.army_entity_id == EntityRow.id)
        .where(EntityRow.world_id == world, ArmyOperationRow.culminated.is_(True))
        .order_by(ArmyOperationRow.army_entity_id)
        .limit(LIST_LINES)
    ):
        found.append(f"the offensive of {army.name} has outrun its supply")
    for admiralty, polity in await session.execute(
        select(AdmiraltyRow, EntityRow)
        .join(EntityRow, EntityRow.id == AdmiraltyRow.polity_entity_id)
        .where(EntityRow.world_id == world, AdmiraltyRow.tonnage > 0)
        .order_by(AdmiraltyRow.tonnage.desc(), AdmiraltyRow.polity_entity_id)
        .limit(LIST_LINES)
    ):
        cap = f", bound to {admiralty.limit_tonnage}" if admiralty.limit_tonnage is not None else ""
        found.append(f"{polity.name} (polity {polity.id}) keeps a fleet of {admiralty.tonnage} tons{cap}")
    return found
