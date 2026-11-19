from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.operations import TheatreRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.operations import QuirkKind
from aerona.domain.enums.polity import ClauseKind, PartyRole, TreatyKind
from aerona.domain.enums.vehicles import VehicleFrame
from aerona.engine.operations import control
from aerona.engine.operations.admiralty import limited_pair
from aerona.engine.operations.expeditions import companions_for, on_expedition
from aerona.engine.operations.supply import draw
from aerona.engine.polity.accords import Clause, sign
from aerona.engine.primitives.queries import living_entity
from aerona.engine.services.war import current_war
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
OWNERS = frozenset({EntityType.POLITY, EntityType.SETTLEMENT, EntityType.PEOPLE})
MORTALS = frozenset({EntityType.MORTAL})
POLITIES = frozenset({EntityType.POLITY})


class SendExpeditionInput(ToolInput):
    leader_id: int
    target_id: int
    reason: Reason


class StockDepotInput(ToolInput):
    owner_id: int
    region_id: int
    reason: Reason


class SteerTheatreInput(ToolInput):
    theatre_id: int
    priority: int = Field(ge=0, le=PERCENT)
    reason: Reason


class MarkQuirkInput(ToolInput):
    mortal_id: int
    kind: QuirkKind
    reason: Reason


class LimitFleetsInput(ToolInput):
    first_id: int
    second_id: int
    tonnage: int = Field(ge=0, le=1_000_000)
    frame: VehicleFrame | None = None
    reason: Reason


async def reached(call: SonCall, entity_id: int, kinds: frozenset[EntityType], refused: SonResult, why: str) -> EntityRow:
    entity = await living_entity(call.session, entity_id)
    if entity is None or entity.entity_type not in kinds:
        fail(refused, why=why)
    await ensure_in_reach(call, entity)
    if held(entity.id):
        fail(refused, why="a stronger hand holds it")
    return entity


async def send_expedition(call: SonCall, args: SendExpeditionInput) -> str:
    leader = await reached(call, args.leader_id, MORTALS, SonResult.EXPEDITION_REFUSED, "there is no such mortal")
    target = await living_entity(call.session, args.target_id)
    if target is None or target.id == leader.id:
        fail(SonResult.EXPEDITION_REFUSED, why="there is no such place to reach")
    away = await on_expedition(call.tick)
    if leader.id in away:
        fail(SonResult.EXPEDITION_REFUSED, why=f"{leader.name} is already on an expedition")
    companions = await companions_for(call.tick, leader, away)
    try:
        row = await control.send_expedition(call.tick, leader.id, target.id, [mortal.id for mortal in companions], call.son.id)
    except ValidationFailedError as error:
        fail(SonResult.EXPEDITION_REFUSED, why=str(error).rstrip("."))
    call.target(leader.id)
    await call.record(
        "tools.son.send_expedition",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.TARGET: target.id, IncidentRole.SUBJECT: leader.id},
        facts={"leader_detail": str(leader.name), "reason": args.reason},
        kind=ChronicleKind.WORLD,
    )
    return result(SonResult.EXPEDITION_SENT, leader=leader.name, target=target.name, legs=row.legs_total, party=len(companions) + 1)


async def stock_depot(call: SonCall, args: StockDepotInput) -> str:
    owner = await reached(call, args.owner_id, OWNERS, SonResult.DEPOT_REFUSED, "there is no such realm or people")
    land = await reached(call, args.region_id, frozenset({EntityType.REGION}), SonResult.DEPOT_REFUSED, "there is no such land")
    table = call.tick.rules.supply_network
    try:
        depot = await control.found_depot(call.tick, owner.id, land.id, field=True, capacity=table.field_capacity, supplies=0)
    except ValidationFailedError as error:
        fail(SonResult.DEPOT_REFUSED, why=str(error).rstrip("."))
    depot.supplies = await draw(call.tick, owner, depot.capacity)
    call.target(land.id)
    await call.record(
        "tools.son.stock_depot",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: [owner.id, land.id]},
        facts={"owner_detail": str(owner.name), "land": str(land.name), "reason": args.reason},
        kind=ChronicleKind.WORLD,
    )
    return result(SonResult.DEPOT_STOCKED, owner=owner.name, land=land.name, supplies=depot.supplies)


async def steer_theatre(call: SonCall, args: SteerTheatreInput) -> str:
    row = await call.session.get(TheatreRow, args.theatre_id)
    if row is None:
        fail(SonResult.THEATRE_REFUSED, why="there is no such theatre of war")
    owner = await reached(call, row.owner_entity_id, OWNERS, SonResult.THEATRE_REFUSED, "its realm is beyond you")
    try:
        await control.edit_record(call.tick, "theatre", row.id, {"priority": args.priority}, [])
    except ValidationFailedError as error:
        fail(SonResult.THEATRE_REFUSED, why=str(error).rstrip("."))
    call.target(owner.id)
    await call.record(
        "tools.son.steer_theatre",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: owner.id},
        facts={"owner_detail": str(owner.name), "priority": args.priority, "reason": args.reason},
        kind=ChronicleKind.WAR,
    )
    return result(SonResult.THEATRE_STEERED, owner=owner.name, priority=args.priority)


async def mark_quirk(call: SonCall, args: MarkQuirkInput) -> str:
    mortal = await reached(call, args.mortal_id, MORTALS, SonResult.QUIRK_REFUSED, "there is no such mortal")
    try:
        await control.give_quirk(call.tick, mortal.id, args.kind, None)
    except ValidationFailedError as error:
        fail(SonResult.QUIRK_REFUSED, why=str(error).rstrip("."))
    call.target(mortal.id)
    await call.record(
        "tools.son.mark_quirk",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: mortal.id},
        facts={"mortal": str(mortal.name), "quirk": args.kind, "reason": args.reason},
        kind=ChronicleKind.WORLD,
    )
    return result(SonResult.QUIRK_MARKED, mortal=mortal.name, quirk=spoken(args.kind))


async def limit_fleets(call: SonCall, args: LimitFleetsInput) -> str:
    first = await reached(call, args.first_id, POLITIES, SonResult.FLEET_LIMIT_REFUSED, "there is no such realm")
    second = await reached(call, args.second_id, POLITIES, SonResult.FLEET_LIMIT_REFUSED, "there is no such realm")
    if first.id == second.id:
        fail(SonResult.FLEET_LIMIT_REFUSED, why="a realm cannot bind its fleet to itself")
    if await current_war(call.session, first.id, second.id) is not None:
        fail(SonResult.FLEET_LIMIT_REFUSED, why="they are at war")
    if await limited_pair(call.tick, first.id, second.id):
        fail(SonResult.FLEET_LIMIT_REFUSED, why="their fleets are already bound")
    cap: dict[str, int | str | bool] = {"tonnage": args.tonnage, **({"frame": args.frame.value} if args.frame is not None else {})}
    treaty = await sign(
        call.tick,
        TreatyKind.NAVAL_LIMIT,
        [(first.id, PartyRole.SIGNATORY), (second.id, PartyRole.SIGNATORY)],
        clauses=[Clause(ClauseKind.FLEET_LIMIT, first.id, second.id, dict(cap)), Clause(ClauseKind.FLEET_LIMIT, second.id, first.id, dict(cap))],
    )
    call.target(treaty.id)
    await call.record(
        "tools.son.limit_fleets",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: [first.id, second.id, treaty.id]},
        facts={"first": str(first.name), "second": str(second.name), "reason": args.reason},
        kind=ChronicleKind.DIPLOMACY,
    )
    return result(SonResult.FLEETS_LIMITED, first=first.name, second=second.name, tonnage=args.tonnage)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [
        ToolSpec(SonToolId.SEND_EXPEDITION, son, SendExpeditionInput, meta, send_expedition),
        ToolSpec(SonToolId.STOCK_DEPOT, son, StockDepotInput, meta, stock_depot),
        ToolSpec(SonToolId.STEER_THEATRE, son, SteerTheatreInput, meta, steer_theatre),
        ToolSpec(SonToolId.MARK_QUIRK, son, MarkQuirkInput, meta, mark_quirk),
        ToolSpec(SonToolId.LIMIT_FLEETS, son, LimitFleetsInput, meta, limit_fleets),
    ]
