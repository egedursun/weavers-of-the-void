from typing import Any

from pydantic import Field
from sqlalchemy import func, select

from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import several
from aerona.db.tables.constructs import ConstructRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import CompanyProfileRow, CompanyShareRow
from aerona.db.tables.made import (
    AugmentRow,
    DataStoreContentRow,
    DataStoreRow,
    FabricationRow,
    MadeRelicRow,
    PatternRightRow,
    ReplicatorLineRow,
    SalvageSiteRow,
    SurveillanceProfileRow,
)
from aerona.db.tables.minds import MindProfileRow, MindStateRow, RemoteBodyRow
from aerona.db.tables.networks import NetworkNodeRow, NetworkProfileRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.body import BodyPart
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.collective import AccountKind, AccountMedium
from aerona.domain.enums.constructs import CommandToken, MindWill
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.made import (
    AugmentKind,
    AugmentMake,
    AugmentSlot,
    Authenticity,
    CompanyCharter,
    DataContent,
    IntrusionAim,
    IntrusionApproach,
    IntrusionTarget,
    RealmAwareness,
    RealmEntry,
    RealmPurpose,
    RelicUse,
    ReplicatorOutput,
    ReplicatorScale,
    SurveillanceFocus,
)
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import MemoryKind, SkillKind
from aerona.domain.enums.minds import MindAffect, MindMaking, MindPurpose, MindSeat, MindUpkeep, StateMedium
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.networks import NetworkAccess, NetworkCarrier, NetworkRole, OutageCause
from aerona.domain.enums.polity import LawKind
from aerona.engine import augments
from aerona.engine.collective.accounts import record
from aerona.engine.constructs import control as constructs
from aerona.engine.economy.purse import give_coin, take_coin
from aerona.engine.made import control
from aerona.engine.made.intrusion import Attempt, intrude
from aerona.engine.made.realms import enter_realm, withdraw
from aerona.engine.made.surveillance import profile_for
from aerona.engine.mind.book import best_skill
from aerona.engine.minds import continuity
from aerona.engine.minds.crimes import binding_crime, copying_crime, mind_crime
from aerona.engine.minds.making import Making, make_mind, missing_craft
from aerona.engine.phases.factions import found_faction
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import connect, living_entity
from aerona.engine.services.community_relations import change_relation
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal import lines
from aerona.tools.mortal.inputs import EnactLawInput
from aerona.tools.mortal.ruler import enact_law, throne_of

MAKERS = (SkillKind.COMPUTING, SkillKind.ENGINEERING, SkillKind.SPELLCRAFT, SkillKind.RITUAL, SkillKind.MECHANICS, SkillKind.SCIENCE)
DEFENCE = 10
SPYING = 15
CONTAINMENT = 15
FABRICATION_STEP = 10
SEATS = {
    EntityType.NETWORK: MindSeat.NETWORK,
    EntityType.STRUCTURE: MindSeat.STRUCTURE,
    EntityType.REGION: MindSeat.PLACE,
    EntityType.SETTLEMENT: MindSeat.PLACE,
    EntityType.ITEM: MindSeat.OBJECT,
}
SHARES_MAX = 100


class MakeMindInput(ToolInput):
    target_id: int
    method: MindMaking = MindMaking.CRAFT
    will: MindWill = MindWill.INSTRUCTED
    purpose: MindPurpose = MindPurpose.SERVANT


class MindInput(ToolInput):
    mind_id: int


class SaveMindInput(MindInput):
    medium: StateMedium = StateMedium.RECORD


class RestoreMindInput(ToolInput):
    state_id: int
    seat_id: int | None = None


class SeatMindInput(MindInput):
    seat_id: int


class MergeMindsInput(ToolInput):
    mind_ids: list[int] = Field(min_length=2, max_length=2)


class InstallAugmentInput(ToolInput):
    body_part: BodyPart | None = None
    kind: AugmentKind = AugmentKind.ENHANCEMENT
    make: AugmentMake = AugmentMake.MADE


class AugmentInput(ToolInput):
    augment_id: int


class TargetInput(ToolInput):
    target_id: int


class BodyInput(ToolInput):
    body_id: int


class BuildNetworkInput(ToolInput):
    carrier: NetworkCarrier = NetworkCarrier.RELAY
    access: NetworkAccess = NetworkAccess.MEMBERS
    member_ids: list[int] = Field(default_factory=list, max_length=12)


class NetworkInput(ToolInput):
    network_id: int


class CutNetworkInput(NetworkInput):
    node_id: int | None = None


class IntrudeInput(ToolInput):
    target: IntrusionTarget = IntrusionTarget.NETWORK
    target_id: int
    aim: IntrusionAim = IntrusionAim.READ


class SystemInput(ToolInput):
    system_id: int


class StoreInput(ToolInput):
    store_id: int


class RecordInput(ToolInput):
    subject_id: int


class CompanyNameInput(ToolInput):
    name: str = Field(min_length=1, max_length=120)


class CompanyInput(ToolInput):
    company_id: int


class BuySharesInput(CompanyInput):
    share: int = Field(default=10, ge=1, le=SHARES_MAX)


class BuildReplicatorInput(ToolInput):
    output: ReplicatorOutput = ReplicatorOutput.GOODS
    feedstock: MaterialKind = MaterialKind.IRON


class LineInput(ToolInput):
    line_id: int


class PatternInput(ToolInput):
    pattern_id: int


class RelicInput(ToolInput):
    item_id: int


class SiteInput(ToolInput):
    site_id: int


class BuildRealmInput(ToolInput):
    host_id: int
    purpose: RealmPurpose = RealmPurpose.DWELLING
    ratio: int = Field(default=100, ge=1, le=10000)


class RealmInput(ToolInput):
    realm_id: int


class ConfineInput(RealmInput):
    target_id: int


class WithdrawInput(RealmInput):
    people_id: int


class SurveillanceInput(ToolInput):
    focus: SurveillanceFocus = SurveillanceFocus.CRIME


class ProvisionInput(ToolInput):
    level: str = Field(default="universal", pattern="^(market|ration|universal|by_status|by_reputation|communal)$")


def why(error: ValidationFailedError) -> str:
    return str(error).rstrip(".")


async def thing(call: MortalCall, node_id: int | None, declined: MortalResult, what: str) -> EntityRow:
    found = await living_entity(call.session, node_id)
    if found is None:
        fail(declined, why=f"there is no such {what}")
    if found.world_id is not None and call.me.world_id is not None and found.world_id != call.me.world_id:
        fail(declined, why=f"that {what} is beyond your world")
    if held(found.id):
        fail(declined, why="a stronger hand holds it")
    return found


async def mine(call: MortalCall, mind_id: int, declined: MortalResult) -> EntityRow:
    found = await thing(call, mind_id, declined, "mind")
    if found.id == call.me.id:
        return found
    profile = await call.session.get(MindProfileRow, found.id)
    if (profile is None or profile.made_by_node_id != call.me.id) and await captive_of(call, found.id) is None:
        fail(declined, why=f"the mind of {found.name} is neither yours, of your making nor held captive by you")
    return found


async def captive_of(call: MortalCall, node_id: int) -> CaptiveRow | None:
    captors = [node for node in (call.me.id, call.me.location_id) if node is not None]
    held_by = select(CaptiveRow).where(CaptiveRow.captive_entity_id == node_id, CaptiveRow.captor_entity_id.in_(captors))
    found: CaptiveRow | None = await call.session.scalar(held_by.limit(1))
    return found


async def seat_for(call: MortalCall, seat_id: int | None, declined: MortalResult) -> tuple[MindSeat, int | None]:
    if seat_id is None:
        return MindSeat.BODY, None
    seat = await thing(call, seat_id, declined, "seat")
    return SEATS.get(seat.entity_type, MindSeat.BODY), seat.id


async def make_mind_tool(call: MortalCall, args: MakeMindInput) -> str:
    target = await thing(call, args.target_id, MortalResult.MIND_MAKING_DECLINED, "thing")
    if target.entity_type is EntityType.MORTAL:
        fail(MortalResult.MIND_MAKING_DECLINED, why="a born being already has its mind")
    lacking = await missing_craft(call.session, call.rules, call.me.id, args.method)
    if lacking is not None:
        fail(MortalResult.MIND_MAKING_DECLINED, why=lacking)
    banned = await law_param(call.session, call.me.location_id or call.me.id, LawKind.MACHINE_LAW, "banned_method")
    if banned == args.method.value:
        fail(MortalResult.MIND_MAKING_DECLINED, why="the law here forbids making minds that way")
    skill = await best_skill(call.session, call.me.id, MAKERS)
    making = Making(
        args.method,
        SEATS.get(target.entity_type, MindSeat.OBJECT),
        target.id,
        args.will,
        args.purpose,
        MindAffect.MODELLED,
        MindUpkeep.MAINTENANCE,
        skill=skill,
    )
    try:
        await make_mind(call.tick, target.id, call.me.id, making)
    except ValidationFailedError as error:
        fail(MortalResult.MIND_MAKING_DECLINED, why=why(error))
    call.target(target.id)
    await call.chronicle(ChronicleKind.CREATION, lines.MAKE_MIND, entity_ids=[call.me.id, target.id], me=call.me.name, name=target.name)
    return result(MortalResult.MIND_MADE, name=target.name)


async def free_mind(call: MortalCall, args: MindInput) -> str:
    target = await mine(call, args.mind_id, MortalResult.MIND_FREEING_DECLINED)
    profile = await call.session.get(MindProfileRow, target.id)
    if profile is None or profile.purpose is MindPurpose.FREE:
        fail(MortalResult.MIND_FREEING_DECLINED, why=f"{target.name} already serves no one")
    profile.purpose = MindPurpose.FREE
    call.target(target.id)
    await call.chronicle(ChronicleKind.ORDER, lines.FREE_MIND, entity_ids=[call.me.id, target.id], me=call.me.name, name=target.name)
    return result(MortalResult.MIND_FREED, name=target.name)


async def bind_mind(call: MortalCall, args: MindInput) -> str:
    target = await mine(call, args.mind_id, MortalResult.MIND_BINDING_DECLINED)
    if target.id == call.me.id:
        fail(MortalResult.MIND_BINDING_DECLINED, why="you cannot bind your own mind")
    try:
        orders = await constructs.rules_of(call.tick, target.id)
        if orders is None:
            await constructs.write_rules(call.tick, target.id, CommandToken.WORD, None, call.me.id)
        else:
            await constructs.edit_record(call.tick, "instruction_set", orders.id, {"command_token": CommandToken.WORD, "holder_node_id": call.me.id}, [])
    except ValidationFailedError as error:
        fail(MortalResult.MIND_BINDING_DECLINED, why=why(error))
    crime = await binding_crime(call.me, await call.session.get(MindProfileRow, target.id))
    if crime is not None:
        await mind_crime(call.tick, call.me.id, crime)
    call.target(target.id)
    await call.chronicle(ChronicleKind.ORDER, lines.BIND_MIND, entity_ids=[call.me.id, target.id], me=call.me.name, name=target.name)
    return result(MortalResult.MIND_BOUND, name=target.name)


async def save_mind_tool(call: MortalCall, args: SaveMindInput) -> str:
    target = await mine(call, args.mind_id, MortalResult.MIND_SAVE_DECLINED)
    try:
        row = await continuity.save_mind(call.tick, target.id, call.me.id, call.me.id, args.medium)
    except ValidationFailedError as error:
        fail(MortalResult.MIND_SAVE_DECLINED, why=why(error))
    if await captive_of(call, target.id) is not None:
        await mind_crime(call.tick, call.me.id, CrimeKind.MIND_THEFT)
    call.target(target.id)
    await call.chronicle(ChronicleKind.WORLD, lines.SAVE_MIND, entity_ids=[call.me.id, target.id], me=call.me.name, name=target.name)
    return result(MortalResult.MIND_SAVED, name=target.name, state=row.id)


async def restore_mind_tool(call: MortalCall, args: RestoreMindInput) -> str:
    state = await call.session.get(MindStateRow, args.state_id)
    if state is None or state.owner_node_id != call.me.id:
        fail(MortalResult.MIND_RESTORE_DECLINED, why="you hold no such saved mind")
    seat, seat_id = await seat_for(call, args.seat_id, MortalResult.MIND_RESTORE_DECLINED)
    try:
        entity = await continuity.restore_mind(call.tick, state.id, seat, seat_id)
    except ValidationFailedError as error:
        fail(MortalResult.MIND_RESTORE_DECLINED, why=why(error))
    call.target(entity.id)
    await call.chronicle(ChronicleKind.WORLD, lines.RESTORE_MIND, entity_ids=[call.me.id, entity.id], me=call.me.name, name=entity.name)
    return result(MortalResult.MIND_RESTORED, name=entity.name)


async def copy_mind_tool(call: MortalCall, args: SeatMindInput) -> str:
    target = await mine(call, args.mind_id, MortalResult.MIND_COPY_DECLINED)
    seat, seat_id = await seat_for(call, args.seat_id, MortalResult.MIND_COPY_DECLINED)
    try:
        copy = await continuity.copy_mind(call.tick, target.id, seat, seat_id)
    except ValidationFailedError as error:
        fail(MortalResult.MIND_COPY_DECLINED, why=why(error))
    source = await call.session.get(MindProfileRow, target.id)
    crime = await copying_crime(call.tick, call.me, source, seat) if source is not None else None
    if crime is not None:
        await mind_crime(call.tick, call.me.id, crime)
    captive = await captive_of(call, target.id)
    if captive is not None and captive.home_entity_id is not None:
        await change_relation(
            call.tick, captive.home_entity_id, call.me.id, -SPYING, MemoryKind.SPIED_ON_US, note="copied the mind of one of ours held captive"
        )
    call.target(copy.id)
    await call.chronicle(ChronicleKind.WORLD, lines.COPY_MIND, entity_ids=[call.me.id, target.id, copy.id], me=call.me.name, name=target.name)
    return result(MortalResult.MIND_COPIED, name=target.name)


async def transfer_mind_tool(call: MortalCall, args: SeatMindInput) -> str:
    target = await mine(call, args.mind_id, MortalResult.MIND_TRANSFER_DECLINED)
    seat, seat_id = await seat_for(call, args.seat_id, MortalResult.MIND_TRANSFER_DECLINED)
    try:
        await continuity.transfer_mind(call.tick, target.id, seat, seat_id)
    except ValidationFailedError as error:
        fail(MortalResult.MIND_TRANSFER_DECLINED, why=why(error))
    call.target(target.id)
    await call.chronicle(ChronicleKind.WORLD, lines.TRANSFER_MIND, entity_ids=[call.me.id, target.id], me=call.me.name, name=target.name)
    return result(MortalResult.MIND_TRANSFERRED, name=target.name)


async def merge_minds_tool(call: MortalCall, args: MergeMindsInput) -> str:
    first = await mine(call, args.mind_ids[0], MortalResult.MIND_MERGE_DECLINED)
    second = await mine(call, args.mind_ids[1], MortalResult.MIND_MERGE_DECLINED)
    try:
        await continuity.merge_minds(call.tick, first.id, second.id)
    except ValidationFailedError as error:
        fail(MortalResult.MIND_MERGE_DECLINED, why=why(error))
    call.target(first.id)
    await call.chronicle(
        ChronicleKind.WORLD, lines.MERGE_MINDS, entity_ids=[call.me.id, first.id, second.id], me=call.me.name, first=first.name, second=second.name
    )
    return result(MortalResult.MINDS_MERGED, first=first.name, second=second.name)


async def install_augment(call: MortalCall, args: InstallAugmentInput) -> str:
    slot = AugmentSlot.PART if args.body_part is not None else AugmentSlot.WHOLE_BODY
    try:
        row = await augments.install(
            call.tick, call.me.id, slot=slot, part=args.body_part, kind=args.kind, make=args.make, quality=50, surgeon_id=call.me.id, effects=[]
        )
    except ValidationFailedError as error:
        fail(MortalResult.AUGMENT_DECLINED, why=why(error))
    call.target(call.me.id)
    await call.chronicle(ChronicleKind.WORLD, lines.INSTALL_AUGMENT, entity_ids=[call.me.id], me=call.me.name, kind=args.kind.value.replace("_", " "))
    return result(MortalResult.AUGMENT_INSTALLED, kind=args.kind.value.replace("_", " "), integration=row.integration)


async def remove_augment(call: MortalCall, args: AugmentInput) -> str:
    row = await call.session.get(AugmentRow, args.augment_id)
    if row is None or row.bearer_node_id != call.me.id:
        fail(MortalResult.AUGMENT_REMOVAL_DECLINED, why="you bear no such augment")
    await augments.remove(call.tick, row.id)
    await call.chronicle(ChronicleKind.WORLD, lines.REMOVE_AUGMENT, entity_ids=[call.me.id], me=call.me.name)
    return result(MortalResult.AUGMENT_REMOVED)


async def link_to(call: MortalCall, args: TargetInput) -> str:
    target = await thing(call, args.target_id, MortalResult.LINK_DECLINED, "mind")
    if target.id == call.me.id:
        fail(MortalResult.LINK_DECLINED, why="you cannot link to yourself")
    await connect(call.session, call.me.id, target.id, BondKind.LINKED_WITH, call.tick.epoch, description="minds linked")
    call.target(target.id)
    await call.chronicle(ChronicleKind.WORLD, lines.LINK_TO, entity_ids=[call.me.id, target.id], me=call.me.name, name=target.name)
    return result(MortalResult.LINKED, name=target.name)


async def run_remote_body(call: MortalCall, args: BodyInput) -> str:
    body = await thing(call, args.body_id, MortalResult.REMOTE_DECLINED, "body")
    if body.id == call.me.id or (await call.session.get(ConstructRow, body.id) is None and body.entity_type is not EntityType.STRUCTURE):
        fail(MortalResult.REMOTE_DECLINED, why=f"{body.name} is not a made body you can run")
    mind = await call.session.get(MindProfileRow, call.me.id)
    allowed = max(1, (mind.capacity if mind is not None else call.rules.minds.baseline_capacity) // call.rules.interfaces.bodies_per_capacity)
    running = int(await call.session.scalar(select(func.count()).where(RemoteBodyRow.mind_node_id == call.me.id, RemoteBodyRow.body_node_id != body.id)) or 0)
    if running >= allowed:
        fail(MortalResult.REMOTE_DECLINED, why=f"your mind can run only {several(allowed, 'remote body', 'remote bodies')} at once")
    row = await call.session.get(RemoteBodyRow, body.id)
    if row is None:
        row = RemoteBodyRow(body_node_id=body.id, mind_node_id=call.me.id, feedback_pct=30, since_epoch=call.tick.epoch, locked=[])
        call.session.add(row)
    row.mind_node_id = call.me.id
    call.target(body.id)
    await call.chronicle(ChronicleKind.WORLD, lines.RUN_REMOTE_BODY, entity_ids=[call.me.id, body.id], me=call.me.name, name=body.name)
    return result(MortalResult.REMOTE_RUNNING, name=body.name)


async def build_network(call: MortalCall, args: BuildNetworkInput) -> str:
    town = await living_entity(call.session, call.me.location_id)
    try:
        row = await control.found_network(call.tick, call.me.id, f"the network of {call.me.name}", args.carrier, town.id if town is not None else None)
        row.access = args.access
        for member in {*args.member_ids, *([town.id] if town is not None else [])}:
            await control.join_network(call.tick, row.network_entity_id, member, NetworkRole.END)
    except ValidationFailedError as error:
        fail(MortalResult.NETWORK_BUILD_DECLINED, why=why(error))
    call.target(row.network_entity_id)
    await call.chronicle(ChronicleKind.CIVILIZATION, lines.BUILD_NETWORK, entity_ids=[call.me.id, row.network_entity_id], me=call.me.name)
    return result(MortalResult.NETWORK_BUILT, carrier=args.carrier.value.replace("_", " "))


async def network_of(call: MortalCall, network_id: int, declined: MortalResult) -> tuple[EntityRow, NetworkProfileRow]:
    node = await thing(call, network_id, declined, "network")
    row = await call.session.get(NetworkProfileRow, node.id)
    if row is None:
        fail(declined, why=f"{node.name} is not a network")
    return node, row


async def join_network(call: MortalCall, args: NetworkInput) -> str:
    node, _ = await network_of(call, args.network_id, MortalResult.NETWORK_JOIN_DECLINED)
    member = call.me.location_id or call.me.id
    present = await call.session.scalar(select(NetworkNodeRow.id).where(NetworkNodeRow.network_entity_id == node.id, NetworkNodeRow.member_node_id == member))
    if present is not None:
        fail(MortalResult.NETWORK_JOIN_DECLINED, why="your home is on it already")
    await control.join_network(call.tick, node.id, member, NetworkRole.END)
    call.target(node.id)
    await call.chronicle(ChronicleKind.CIVILIZATION, lines.JOIN_NETWORK, entity_ids=[call.me.id, node.id], me=call.me.name, name=node.name)
    return result(MortalResult.NETWORK_JOINED, name=node.name)


async def cut_network(call: MortalCall, args: CutNetworkInput) -> str:
    node, _ = await network_of(call, args.network_id, MortalResult.NETWORK_CUT_DECLINED)
    if args.node_id is not None:
        member = await call.session.scalar(
            select(NetworkNodeRow).where(NetworkNodeRow.network_entity_id == node.id, NetworkNodeRow.member_node_id == args.node_id)
        )
        if member is None:
            fail(MortalResult.NETWORK_CUT_DECLINED, why="that member is not on the network")
        await call.session.delete(member)
    else:
        await control.cut_network(call.tick, node.id, OutageCause.SABOTAGE, 1, call.rules.intrusion.outage_severity)
    call.target(node.id)
    await call.chronicle(ChronicleKind.WAR, lines.CUT_NETWORK, entity_ids=[call.me.id, node.id], me=call.me.name, name=node.name)
    return result(MortalResult.NETWORK_CUT, name=node.name)


async def intrude_tool(call: MortalCall, args: IntrudeInput) -> str:
    if held(args.target_id):
        fail(MortalResult.INTRUSION_DECLINED, why="a stronger hand holds it")
    try:
        row = await intrude(call.tick, Attempt(call.me.id, args.target, args.target_id, IntrusionApproach.TECHNICAL, args.aim))
    except ValidationFailedError as error:
        fail(MortalResult.INTRUSION_DECLINED, why=why(error))
    await call.chronicle(ChronicleKind.WAR, lines.INTRUDE, entity_ids=[call.me.id], me=call.me.name)
    return result(MortalResult.INTRUSION_MADE, outcome=row.outcome.value.replace("_", " "), found="found" if row.detection >= 50 else "unseen")


async def defend_system(call: MortalCall, args: SystemInput) -> str:
    network = await call.session.get(NetworkProfileRow, args.system_id)
    store = await call.session.get(DataStoreRow, args.system_id) if network is None else None
    guarded = network or store
    if guarded is None or held(args.system_id):
        fail(MortalResult.DEFENCE_DECLINED, why="there is no such network or store you can guard")
    skill = await best_skill(call.session, call.me.id, (SkillKind.COMPUTING, SkillKind.CRYPTOGRAPHY, SkillKind.RITUAL))
    guarded.security = clamp_percent(guarded.security + DEFENCE + skill // 10)
    await call.chronicle(ChronicleKind.WORLD, lines.DEFEND_SYSTEM, entity_ids=[call.me.id], me=call.me.name)
    return result(MortalResult.SYSTEM_DEFENDED, security=guarded.security)


async def leak_records(call: MortalCall, args: StoreInput) -> str:
    store = await call.session.get(DataStoreRow, args.store_id)
    if store is None or held(store.holder_node_id):
        fail(MortalResult.LEAK_DECLINED, why="there is no such store")
    secrets = list(
        await call.session.scalars(
            select(DataStoreContentRow).where(DataStoreContentRow.store_id == store.id, DataStoreContentRow.content == DataContent.SECRET)
        )
    )
    if not secrets:
        fail(MortalResult.LEAK_DECLINED, why="it holds no secrets")
    for secret in secrets:
        if "content" not in secret.locked:
            secret.content = DataContent.KNOWLEDGE
    await call.chronicle(ChronicleKind.WORLD, lines.LEAK_RECORDS, entity_ids=[call.me.id], me=call.me.name)
    return result(MortalResult.RECORDS_LEAKED, count=len(secrets))


async def write_record(call: MortalCall, subject_id: int, authenticity: Authenticity, declined: MortalResult) -> EntityRow:
    subject = await thing(call, subject_id, declined, "subject")
    town = await living_entity(call.session, call.me.location_id)
    if town is None:
        fail(declined, why="you have no home to keep the record")
    row = await record(
        call.tick, town, AccountKind.FOLK_MEMORY, fidelity=80, stances={}, subject_id=subject.id, medium=AccountMedium.BOOK, author_id=call.me.id
    )
    if row is None:
        fail(declined, why="a stronger hand holds your home")
    row.authenticity = authenticity
    return subject


async def publish(call: MortalCall, args: RecordInput) -> str:
    subject = await write_record(call, args.subject_id, Authenticity.GENUINE, MortalResult.PUBLISH_DECLINED)
    await call.chronicle(ChronicleKind.CULTURE, lines.PUBLISH, entity_ids=[call.me.id, subject.id], me=call.me.name, name=subject.name)
    return result(MortalResult.PUBLISHED, name=subject.name)


async def forge_record(call: MortalCall, args: RecordInput) -> str:
    subject = await write_record(call, args.subject_id, Authenticity.FORGED, MortalResult.FORGERY_DECLINED)
    await call.chronicle(ChronicleKind.CULTURE, lines.FORGE_RECORD, entity_ids=[call.me.id, subject.id], me=call.me.name, name=subject.name)
    return result(MortalResult.RECORD_FORGED, name=subject.name)


async def found_company(call: MortalCall, args: CompanyNameInput) -> str:
    town = await living_entity(call.session, call.me.location_id)
    if town is None or held(town.id):
        fail(MortalResult.COMPANY_DECLINED, why="you have no home to found it in")
    company = await found_faction(call.tick, town, FactionKind.CHARTERED_COMPANY)
    company.name = args.name
    call.session.add(
        CompanyProfileRow(faction_entity_id=company.id, charter=CompanyCharter.FREE, headquarters_entity_id=town.id, chartered_epoch=call.tick.epoch, locked=[])
    )
    call.session.add(CompanyShareRow(company_entity_id=company.id, holder_node_id=call.me.id, share=SHARES_MAX, locked=False))
    call.target(company.id)
    await call.chronicle(ChronicleKind.CIVILIZATION, lines.FOUND_COMPANY, entity_ids=[call.me.id, company.id], me=call.me.name, name=company.name)
    return result(MortalResult.COMPANY_FOUNDED, name=company.name)


async def company_of(call: MortalCall, company_id: int, declined: MortalResult) -> tuple[EntityRow, CompanyProfileRow]:
    node = await thing(call, company_id, declined, "company")
    row = await call.session.get(CompanyProfileRow, node.id)
    if row is None:
        fail(declined, why=f"{node.name} is not a company")
    return node, row


async def charter_company(call: MortalCall, args: CompanyInput) -> str:
    realm = await throne_of(call)
    node, row = await company_of(call, args.company_id, MortalResult.CHARTER_DECLINED)
    row.charter, row.polity_entity_id, row.chartered_epoch = CompanyCharter.CHARTERED, realm.entity.id, call.tick.epoch
    call.target(node.id)
    await call.chronicle(ChronicleKind.CIVILIZATION, lines.CHARTER_COMPANY, entity_ids=[call.me.id, node.id], me=call.me.name, name=node.name)
    return result(MortalResult.COMPANY_CHARTERED, name=node.name, realm=realm.entity.name)


async def buy_shares(call: MortalCall, args: BuySharesInput) -> str:
    node, _ = await company_of(call, args.company_id, MortalResult.SHARES_DECLINED)
    held_now = int(
        await call.session.scalar(select(func.coalesce(func.sum(CompanyShareRow.share), 0)).where(CompanyShareRow.company_entity_id == node.id)) or 0
    )
    mine_now = await call.session.get(CompanyShareRow, (node.id, call.me.id))
    free = SHARES_MAX - held_now
    if args.share > free:
        fail(MortalResult.SHARES_DECLINED, why=f"only {free} of 100 parts are free")
    if not await take_coin(call.session, call.rules, call.me, args.share):
        fail(MortalResult.SHARES_DECLINED, why="you cannot pay for them")
    await give_coin(call.session, call.rules, node, args.share)
    if mine_now is None:
        call.session.add(CompanyShareRow(company_entity_id=node.id, holder_node_id=call.me.id, share=args.share, locked=False))
    else:
        mine_now.share += args.share
    call.target(node.id)
    await call.chronicle(ChronicleKind.CIVILIZATION, lines.BUY_SHARES, entity_ids=[call.me.id, node.id], me=call.me.name, name=node.name)
    return result(MortalResult.SHARES_BOUGHT, name=node.name, share=args.share)


async def build_replicator(call: MortalCall, args: BuildReplicatorInput) -> str:
    town = await living_entity(call.session, call.me.location_id)
    if town is None or town.location_id is None:
        fail(MortalResult.REPLICATOR_DECLINED, why="you have no land to start it in")
    draft = control.LineDraft(
        f"the line of {call.me.name}", ReplicatorScale.MACHINE, args.feedstock, args.output, 10, 5, 80, True, call.me.id, call.me.id, town.location_id, 10
    )
    try:
        row = await control.found_line(call.tick, draft)
    except ValidationFailedError as error:
        fail(MortalResult.REPLICATOR_DECLINED, why=why(error))
    await call.chronicle(ChronicleKind.CIVILIZATION, lines.BUILD_REPLICATOR, entity_ids=[call.me.id], me=call.me.name, name=row.name)
    return result(MortalResult.REPLICATOR_BUILT, name=row.name)


async def contain_replicator(call: MortalCall, args: LineInput) -> str:
    line = await call.session.get(ReplicatorLineRow, args.line_id)
    if line is None or (line.owner_node_id is not None and held(line.owner_node_id)):
        fail(MortalResult.CONTAINMENT_DECLINED, why="there is no such line")
    line.containment = clamp_percent(line.containment + CONTAINMENT)
    await call.chronicle(ChronicleKind.WORLD, lines.CONTAIN_REPLICATOR, entity_ids=[call.me.id], me=call.me.name, name=line.name)
    return result(MortalResult.REPLICATOR_CONTAINED, name=line.name, containment=line.containment)


async def fabricate(call: MortalCall, _args: ToolInput) -> str:
    town = await living_entity(call.session, call.me.location_id)
    if town is None or town.entity_type is not EntityType.SETTLEMENT or held(town.id):
        fail(MortalResult.FABRICATION_DECLINED, why="you have no town to make goods in")
    row = await call.session.get(FabricationRow, town.id)
    if row is None:
        row = FabricationRow(settlement_entity_id=town.id, share_pct=0, dividend_pct=0, updated_epoch=call.tick.epoch, locked=[])
        call.session.add(row)
    row.share_pct = clamp_percent(row.share_pct + FABRICATION_STEP)
    await call.chronicle(ChronicleKind.CIVILIZATION, lines.FABRICATE, entity_ids=[call.me.id, town.id], me=call.me.name, town=town.name)
    return result(MortalResult.FABRICATED, town=town.name, share=row.share_pct)


async def license_pattern(call: MortalCall, args: PatternInput) -> str:
    pattern = await call.session.get(PatternRightRow, args.pattern_id)
    if pattern is None:
        fail(MortalResult.LICENCE_DECLINED, why="there is no such pattern")
    holder = await living_entity(call.session, pattern.holder_node_id)
    if not pattern.open and holder is not None:
        if not await take_coin(call.session, call.rules, call.me, pattern.licence_fee):
            fail(MortalResult.LICENCE_DECLINED, why="you cannot pay its fee")
        await give_coin(call.session, call.rules, holder, pattern.licence_fee)
    await call.chronicle(ChronicleKind.CIVILIZATION, lines.LICENSE_PATTERN, entity_ids=[call.me.id], me=call.me.name)
    return result(MortalResult.PATTERN_LICENSED, fee=0 if pattern.open else pattern.licence_fee)


async def study_relic(call: MortalCall, args: RelicInput) -> str:
    item = await thing(call, args.item_id, MortalResult.STUDY_DECLINED, "relic")
    relic = await call.session.get(MadeRelicRow, item.id)
    if relic is None or not relic.is_relic:
        fail(MortalResult.STUDY_DECLINED, why=f"{item.name} holds nothing lost to study")
    relic.use = RelicUse.REPURPOSED if "use" not in relic.locked else relic.use
    if "understood_pct" not in relic.locked:
        relic.understood_pct = clamp_percent(relic.understood_pct + call.rules.made_relics.study_gain)
    call.target(item.id)
    await call.chronicle(ChronicleKind.CULTURE, lines.STUDY_RELIC, entity_ids=[call.me.id, item.id], me=call.me.name, name=item.name)
    return result(MortalResult.RELIC_STUDIED, name=item.name, understood=relic.understood_pct)


async def salvage(call: MortalCall, args: SiteInput) -> str:
    site = await call.session.get(SalvageSiteRow, args.site_id)
    if site is None or site.yield_left <= 0 or held(site.site_entity_id):
        fail(MortalResult.SALVAGE_DECLINED, why="there is nothing left to salvage there")
    if site.rights_holder_node_id not in {None, call.me.id}:
        fail(MortalResult.SALVAGE_DECLINED, why="another holds the right to salvage it")
    amount = min(site.yield_left, call.rules.made_relics.salvage_yield)
    await give_coin(call.session, call.rules, call.me, amount)
    site.yield_left -= amount
    site.last_salvaged_epoch = call.tick.epoch
    await call.chronicle(ChronicleKind.WORLD, lines.SALVAGE, entity_ids=[call.me.id, site.site_entity_id], me=call.me.name)
    return result(MortalResult.SALVAGED, amount=amount)


async def build_realm(call: MortalCall, args: BuildRealmInput) -> str:
    host = await thing(call, args.host_id, MortalResult.REALM_BUILD_DECLINED, "host")
    draft = control.RealmDraft(
        f"the realm of {call.me.name}", call.me.id, host.id, args.purpose, args.ratio, RealmEntry.INTERFACE, RealmAwareness.KNOWS, MindUpkeep.MAINTENANCE
    )
    row = await control.make_realm(call.tick, draft)
    await call.chronicle(ChronicleKind.CREATION, lines.BUILD_REALM, entity_ids=[call.me.id, row.dimension_id], me=call.me.name, host=host.name)
    return result(MortalResult.REALM_BUILT, host=host.name, ratio=row.time_ratio_pct)


async def enter_realm_tool(call: MortalCall, args: RealmInput) -> str:
    try:
        await enter_realm(call.tick, call.me.id, args.realm_id)
    except ValidationFailedError as error:
        fail(MortalResult.REALM_ENTRY_DECLINED, why=why(error))
    await call.chronicle(ChronicleKind.WORLD, lines.ENTER_REALM, entity_ids=[call.me.id], me=call.me.name)
    return result(MortalResult.REALM_ENTERED)


async def confine_in_realm(call: MortalCall, args: ConfineInput) -> str:
    target = await thing(call, args.target_id, MortalResult.CONFINEMENT_DECLINED, "mind")
    if await captive_of(call, target.id) is None:
        await throne_of(call)
    try:
        await enter_realm(call.tick, target.id, args.realm_id)
    except ValidationFailedError as error:
        fail(MortalResult.CONFINEMENT_DECLINED, why=why(error))
    call.target(target.id)
    await call.chronicle(ChronicleKind.ORDER, lines.CONFINE_IN_REALM, entity_ids=[call.me.id, target.id], me=call.me.name, name=target.name)
    return result(MortalResult.CONFINED, name=target.name)


async def withdraw_people(call: MortalCall, args: WithdrawInput) -> str:
    people = await thing(call, args.people_id, MortalResult.WITHDRAWAL_DECLINED, "people")
    await throne_of(call)
    try:
        moved = await withdraw(call.tick, people.id, args.realm_id)
    except ValidationFailedError as error:
        fail(MortalResult.WITHDRAWAL_DECLINED, why=why(error))
    call.target(people.id)
    await call.chronicle(ChronicleKind.CIVILIZATION, lines.WITHDRAW_PEOPLE, entity_ids=[call.me.id, people.id], me=call.me.name, name=people.name)
    return result(MortalResult.PEOPLE_WITHDRAWN, name=people.name, count=moved)


async def set_surveillance(call: MortalCall, args: SurveillanceInput) -> str:
    realm = await throne_of(call)
    if held(realm.entity.id):
        fail(MortalResult.SURVEILLANCE_DECLINED, why="a stronger hand holds your realm")
    row: SurveillanceProfileRow = await profile_for(call.tick, realm.entity.id)
    row.focus = args.focus
    call.target(realm.entity.id)
    await call.chronicle(ChronicleKind.CIVILIZATION, lines.SET_SURVEILLANCE, entity_ids=[call.me.id, realm.entity.id], me=call.me.name, realm=realm.entity.name)
    return result(MortalResult.SURVEILLANCE_SET, realm=realm.entity.name, focus=args.focus.value.replace("_", " "))


async def set_provision(call: MortalCall, args: ProvisionInput) -> str:
    return await enact_law(call, EnactLawInput(kind=LawKind.PROVISION_LAW, params={"level": args.level}))


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.MAKE_MIND, mortal, MakeMindInput, meta, make_mind_tool),
        ToolSpec(MortalToolId.FREE_MIND, mortal, MindInput, meta, free_mind),
        ToolSpec(MortalToolId.BIND_MIND, mortal, MindInput, meta, bind_mind),
        ToolSpec(MortalToolId.SAVE_MIND, mortal, SaveMindInput, meta, save_mind_tool),
        ToolSpec(MortalToolId.RESTORE_MIND, mortal, RestoreMindInput, meta, restore_mind_tool),
        ToolSpec(MortalToolId.COPY_MIND, mortal, SeatMindInput, meta, copy_mind_tool),
        ToolSpec(MortalToolId.TRANSFER_MIND, mortal, SeatMindInput, meta, transfer_mind_tool),
        ToolSpec(MortalToolId.MERGE_MINDS, mortal, MergeMindsInput, meta, merge_minds_tool),
        ToolSpec(MortalToolId.INSTALL_AUGMENT, mortal, InstallAugmentInput, meta, install_augment),
        ToolSpec(MortalToolId.REMOVE_AUGMENT, mortal, AugmentInput, meta, remove_augment),
        ToolSpec(MortalToolId.LINK_TO, mortal, TargetInput, meta, link_to),
        ToolSpec(MortalToolId.RUN_REMOTE_BODY, mortal, BodyInput, meta, run_remote_body),
        ToolSpec(MortalToolId.BUILD_NETWORK, mortal, BuildNetworkInput, meta, build_network),
        ToolSpec(MortalToolId.JOIN_NETWORK, mortal, NetworkInput, meta, join_network),
        ToolSpec(MortalToolId.CUT_NETWORK, mortal, CutNetworkInput, meta, cut_network),
        ToolSpec(MortalToolId.INTRUDE, mortal, IntrudeInput, meta, intrude_tool),
        ToolSpec(MortalToolId.DEFEND_SYSTEM, mortal, SystemInput, meta, defend_system),
        ToolSpec(MortalToolId.LEAK_RECORDS, mortal, StoreInput, meta, leak_records),
        ToolSpec(MortalToolId.PUBLISH, mortal, RecordInput, meta, publish),
        ToolSpec(MortalToolId.FORGE_RECORD, mortal, RecordInput, meta, forge_record),
        ToolSpec(MortalToolId.FOUND_COMPANY, mortal, CompanyNameInput, meta, found_company),
        ToolSpec(MortalToolId.CHARTER_COMPANY, mortal, CompanyInput, meta, charter_company),
        ToolSpec(MortalToolId.BUY_SHARES, mortal, BuySharesInput, meta, buy_shares),
        ToolSpec(MortalToolId.BUILD_REPLICATOR, mortal, BuildReplicatorInput, meta, build_replicator),
        ToolSpec(MortalToolId.CONTAIN_REPLICATOR, mortal, LineInput, meta, contain_replicator),
        ToolSpec(MortalToolId.FABRICATE, mortal, ToolInput, meta, fabricate),
        ToolSpec(MortalToolId.LICENSE_PATTERN, mortal, PatternInput, meta, license_pattern),
        ToolSpec(MortalToolId.STUDY_RELIC, mortal, RelicInput, meta, study_relic),
        ToolSpec(MortalToolId.SALVAGE, mortal, SiteInput, meta, salvage),
        ToolSpec(MortalToolId.BUILD_REALM, mortal, BuildRealmInput, meta, build_realm),
        ToolSpec(MortalToolId.ENTER_REALM, mortal, RealmInput, meta, enter_realm_tool),
        ToolSpec(MortalToolId.CONFINE_IN_REALM, mortal, ConfineInput, meta, confine_in_realm),
        ToolSpec(MortalToolId.WITHDRAW_PEOPLE, mortal, WithdrawInput, meta, withdraw_people),
        ToolSpec(MortalToolId.SET_SURVEILLANCE, mortal, SurveillanceInput, meta, set_surveillance),
        ToolSpec(MortalToolId.SET_PROVISION, mortal, ProvisionInput, meta, set_provision),
    ]
