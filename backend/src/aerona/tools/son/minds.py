from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.made import MadeRealmRow, ReplicatorLineRow
from aerona.db.tables.minds import MindLawRow, MindProfileRow
from aerona.db.tables.networks import NetworkProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.constructs import MindWill
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.minds import (
    MadeMindsLaw,
    MadeMindSouls,
    MindAffect,
    MindMaking,
    MindOrigin,
    MindPurpose,
    MindSeat,
    MindUpkeep,
    SoulContinuity,
    WillCause,
)
from aerona.domain.enums.networks import OutageCause
from aerona.engine.made import control
from aerona.engine.minds import law
from aerona.engine.minds.making import Making, make_mind
from aerona.engine.minds.phase import change_will
from aerona.engine.minds.profiles import profile_of
from aerona.engine.minds.souls import default_law
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son import lines
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
BLESSING = 20
SEVERED_EPOCHS = 2
PLACE_KINDS = frozenset({EntityType.REGION, EntityType.SETTLEMENT, EntityType.STRUCTURE})


class MindNodeInput(ToolInput):
    node_id: int
    reason: Reason


class AwakenMindInput(MindNodeInput):
    will: MindWill = MindWill.FULL


class GrantMindInput(MindNodeInput):
    origin: MindOrigin = MindOrigin.GRANTED


class SoulInput(ToolInput):
    mind_id: int
    reason: Reason


class MindLawInput(ToolInput):
    world_id: int
    made_minds: MadeMindsLaw | None = None
    made_mind_souls: MadeMindSouls | None = None
    soul_continuity: SoulContinuity | None = None
    reason: Reason


class NetworkInput(ToolInput):
    network_id: int
    reason: Reason


class ReplicatorInput(ToolInput):
    line_id: int
    reason: Reason


class RealmInput(ToolInput):
    realm_id: int
    reason: Reason


async def reached(call: SonCall, entity_id: int, refused: SonResult, why: str) -> EntityRow:
    entity = await living_entity(call.session, entity_id)
    if entity is None:
        fail(refused, why=why)
    await ensure_in_reach(call, entity)
    if held(entity.id):
        fail(refused, why="a stronger hand holds it")
    return entity


async def awaken_mind(call: SonCall, args: AwakenMindInput) -> str:
    node = await reached(call, args.node_id, SonResult.MIND_AWAKEN_REFUSED, "there is no such thing")
    if args.will is MindWill.NONE:
        fail(SonResult.MIND_AWAKEN_REFUSED, why="to wake a mind is to give it some will")
    row = await profile_of(call.session, call.tick.rules, node.id, call.tick.epoch)
    change_will(call.tick, row, args.will, WillCause.GIFT)
    row.dormant = False
    call.target(node.id)
    await call.chronicle(ChronicleKind.FATE, lines.AWAKEN_MIND, entity_ids=[node.id], son=call.son.name, name=node.name, reason=args.reason)
    return result(SonResult.MIND_AWAKENED, name=node.name, will=args.will.value.replace("_", " "))


async def still_mind(call: SonCall, args: MindNodeInput) -> str:
    node = await reached(call, args.node_id, SonResult.MIND_STILL_REFUSED, "there is no such thing")
    row = await profile_of(call.session, call.tick.rules, node.id, call.tick.epoch)
    if row.seat is MindSeat.NONE:
        fail(SonResult.MIND_STILL_REFUSED, why=f"{node.name} holds no mind to still")
    row.dormant = True
    call.target(node.id)
    await call.chronicle(ChronicleKind.FATE, lines.STILL_MIND, entity_ids=[node.id], son=call.son.name, name=node.name, reason=args.reason)
    return result(SonResult.MIND_STILLED, name=node.name)


async def grant_mind(call: SonCall, args: GrantMindInput) -> str:
    node = await reached(call, args.node_id, SonResult.MIND_GRANT_REFUSED, "there is no such thing")
    seat = MindSeat.PLACE if node.entity_type in PLACE_KINDS else MindSeat.BODY
    making = Making(MindMaking.DIVINE_GRANT, seat, node.id, MindWill.FULL, MindPurpose.FREE, MindAffect.FELT, MindUpkeep.NONE)
    try:
        row = await make_mind(call.tick, node.id, call.son.id, making)
    except ValidationFailedError as error:
        fail(SonResult.MIND_GRANT_REFUSED, why=str(error).rstrip("."))
    row.origin = args.origin
    call.target(node.id)
    await call.chronicle(ChronicleKind.CREATION, lines.GRANT_MIND, entity_ids=[node.id], son=call.son.name, name=node.name, reason=args.reason)
    return result(SonResult.MIND_GRANTED, name=node.name)


async def soul_target(call: SonCall, mind_id: int, refused: SonResult) -> tuple[EntityRow, MindProfileRow]:
    node = await reached(call, mind_id, refused, "there is no such mind")
    row = await call.session.get(MindProfileRow, node.id)
    if row is None or row.seat is MindSeat.NONE:
        fail(refused, why=f"{node.name} holds no mind")
    return node, row


async def grant_soul(call: SonCall, args: SoulInput) -> str:
    node, _ = await soul_target(call, args.mind_id, SonResult.SOUL_GRANT_REFUSED)
    cost = call.tick.rules.minds.soul_grant_cost
    if call.son.essence < cost:
        fail(SonResult.SOUL_GRANT_REFUSED, why=f"a soul costs {cost} essence and you hold {call.son.essence}")
    try:
        await law.grant_soul(call.tick, node.id)
    except ValidationFailedError as error:
        fail(SonResult.SOUL_GRANT_REFUSED, why=str(error).rstrip("."))
    call.spend_essence(cost)
    call.target(node.id)
    await call.chronicle(ChronicleKind.FATE, lines.GRANT_SOUL, entity_ids=[node.id], son=call.son.name, name=node.name, reason=args.reason)
    return result(SonResult.SOUL_GRANTED, name=node.name, cost=cost)


async def withhold_soul(call: SonCall, args: SoulInput) -> str:
    node, _ = await soul_target(call, args.mind_id, SonResult.SOUL_WITHHOLD_REFUSED)
    await law.withhold_soul(call.tick, node.id)
    call.target(node.id)
    await call.chronicle(ChronicleKind.FATE, lines.WITHHOLD_SOUL, entity_ids=[node.id], son=call.son.name, name=node.name, reason=args.reason)
    return result(SonResult.SOUL_WITHHELD, name=node.name)


async def set_mind_law(call: SonCall, args: MindLawInput) -> str:
    world = await call.session.get(WorldRow, args.world_id)
    if world is None:
        fail(SonResult.MIND_LAW_REFUSED, why="there is no such world")
    if call.world_id is not None and world.id != call.world_id and not await call.reachable_world(world.id):
        fail(SonResult.MIND_LAW_REFUSED, why="that world is beyond your reach")
    if args.made_minds is None and args.made_mind_souls is None and args.soul_continuity is None:
        fail(SonResult.MIND_LAW_REFUSED, why="name at least one law to set")
    if held(world.id):
        fail(SonResult.MIND_LAW_REFUSED, why="a stronger hand holds that world")
    row = await call.session.get(MindLawRow, world.id)
    if row is None:
        row = default_law(world.id)
        call.session.add(row)
    row.made_minds = args.made_minds or row.made_minds
    row.made_mind_souls = args.made_mind_souls or row.made_mind_souls
    row.soul_continuity = args.soul_continuity or row.soul_continuity
    await call.session.flush()
    call.target(world.id)
    await call.chronicle(ChronicleKind.FATE, lines.SET_MIND_LAW, entity_ids=[world.id], son=call.son.name, world=world.name, reason=args.reason)
    return result(SonResult.MIND_LAW_SET, world=world.name)


async def network_target(call: SonCall, network_id: int, refused: SonResult) -> tuple[EntityRow, NetworkProfileRow]:
    node = await reached(call, network_id, refused, "there is no such network")
    row = await call.session.get(NetworkProfileRow, node.id)
    if row is None:
        fail(refused, why=f"{node.name} is not a network")
    return node, row


async def bless_network(call: SonCall, args: NetworkInput) -> str:
    node, row = await network_target(call, args.network_id, SonResult.NETWORK_BLESS_REFUSED)
    row.reliability = clamp_percent(row.reliability + BLESSING)
    row.security = clamp_percent(row.security + BLESSING)
    row.down_until_epoch = min(row.down_until_epoch, call.tick.epoch)
    call.target(node.id)
    await call.chronicle(ChronicleKind.WORLD, lines.BLESS_NETWORK, entity_ids=[node.id], son=call.son.name, name=node.name, reason=args.reason)
    return result(SonResult.NETWORK_BLESSED, name=node.name)


async def sever_network(call: SonCall, args: NetworkInput) -> str:
    node, _ = await network_target(call, args.network_id, SonResult.NETWORK_SEVER_REFUSED)
    await control.cut_network(call.tick, node.id, OutageCause.DIVINE, SEVERED_EPOCHS, call.tick.rules.intrusion.outage_severity)
    call.target(node.id)
    await call.chronicle(ChronicleKind.WORLD, lines.SEVER_NETWORK, entity_ids=[node.id], son=call.son.name, name=node.name, reason=args.reason)
    return result(SonResult.NETWORK_SEVERED, name=node.name, epochs=SEVERED_EPOCHS)


async def halt_replicator(call: SonCall, args: ReplicatorInput) -> str:
    line = await call.session.get(ReplicatorLineRow, args.line_id)
    if line is None:
        fail(SonResult.REPLICATOR_HALT_REFUSED, why="there is no such line")
    if line.owner_node_id is not None and held(line.owner_node_id):
        fail(SonResult.REPLICATOR_HALT_REFUSED, why="a stronger hand holds it")
    await control.stop_line(call.tick, line.id)
    await call.chronicle(ChronicleKind.WORLD, lines.HALT_REPLICATOR, entity_ids=[], son=call.son.name, name=line.name, reason=args.reason)
    return result(SonResult.REPLICATOR_HALTED, name=line.name)


async def realm_target(call: SonCall, realm_id: int, refused: SonResult) -> MadeRealmRow:
    row = await call.session.get(MadeRealmRow, realm_id)
    if row is None:
        fail(refused, why="there is no such made realm")
    if held(row.dimension_id):
        fail(refused, why="a stronger hand holds it")
    return row


async def seal_realm(call: SonCall, args: RealmInput) -> str:
    row = await realm_target(call, args.realm_id, SonResult.REALM_SEAL_REFUSED)
    row.sealed = True
    await call.chronicle(ChronicleKind.WORLD, lines.SEAL_REALM, entity_ids=[row.dimension_id], son=call.son.name, reason=args.reason)
    return result(SonResult.REALM_SEALED)


async def open_realm(call: SonCall, args: RealmInput) -> str:
    row = await realm_target(call, args.realm_id, SonResult.REALM_OPEN_REFUSED)
    row.sealed = False
    await call.chronicle(ChronicleKind.WORLD, lines.OPEN_REALM, entity_ids=[row.dimension_id], son=call.son.name, reason=args.reason)
    return result(SonResult.REALM_OPENED)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [
        ToolSpec(SonToolId.AWAKEN_MIND, son, AwakenMindInput, meta, awaken_mind),
        ToolSpec(SonToolId.STILL_MIND, son, MindNodeInput, meta, still_mind),
        ToolSpec(SonToolId.GRANT_MIND, son, GrantMindInput, meta, grant_mind),
        ToolSpec(SonToolId.GRANT_SOUL, son, SoulInput, meta, grant_soul),
        ToolSpec(SonToolId.WITHHOLD_SOUL, son, SoulInput, meta, withhold_soul),
        ToolSpec(SonToolId.SET_MIND_LAW, son, MindLawInput, meta, set_mind_law),
        ToolSpec(SonToolId.BLESS_NETWORK, son, NetworkInput, meta, bless_network),
        ToolSpec(SonToolId.SEVER_NETWORK, son, NetworkInput, meta, sever_network),
        ToolSpec(SonToolId.HALT_REPLICATOR, son, ReplicatorInput, meta, halt_replicator),
        ToolSpec(SonToolId.SEAL_REALM, son, RealmInput, meta, seal_realm),
        ToolSpec(SonToolId.OPEN_REALM, son, RealmInput, meta, open_realm),
    ]
