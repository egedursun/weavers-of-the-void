from typing import Any

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.constructs import ConstructRow
from aerona.db.tables.contracts import MonsterContractRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.arts import ClubKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.constructs import ContractStatus, OrderCondition, OrderKind
from aerona.engine.arts import control as arts
from aerona.engine.constructs import control as constructs
from aerona.engine.constructs.orders import holder_of
from aerona.engine.primitives.queries import living_entity
from aerona.engine.sacred.places import town_of
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal import lines

FIRST = 1


class ForgeWorkInput(ToolInput):
    original_id: int


class BuyWorkInput(ToolInput):
    artwork_id: int


class FoundClubInput(ToolInput):
    kind: ClubKind | None = None


class TakeContractInput(ToolInput):
    contract_id: int


class CommandConstructInput(ToolInput):
    construct_id: int
    kind: OrderKind
    target_id: int | None = None


def reason_of(error: ValidationFailedError) -> str:
    return str(error).rstrip(".")


async def forge_work(call: MortalCall, args: ForgeWorkInput) -> str:
    original = await living_entity(call.session, args.original_id)
    if original is None or held(original.id):
        fail(MortalResult.FORGERY_DECLINED, why="there is no such thing to copy")
    try:
        row = await arts.forge_work(call.tick, original.id, call.me.id)
    except ValidationFailedError as error:
        fail(MortalResult.FORGERY_DECLINED, why=reason_of(error))
    call.target(row.item_entity_id)
    await call.chronicle(ChronicleKind.CULTURE, lines.FORGE_WORK, entity_ids=[call.me.id, original.id], me=call.me.name, original=original.name)
    return result(MortalResult.FORGERY_MADE, original=original.name, kind=row.kind.value, skill=row.skill)


async def buy_work(call: MortalCall, args: BuyWorkInput) -> str:
    work = await living_entity(call.session, args.artwork_id)
    if work is None or held(work.id):
        fail(MortalResult.PURCHASE_DECLINED, why="there is no such work")
    try:
        sale = await arts.sell_work(call.tick, work.id, call.me.id, None)
    except ValidationFailedError as error:
        fail(MortalResult.PURCHASE_DECLINED, why=reason_of(error))
    call.target(work.id)
    await call.chronicle(ChronicleKind.TRADE, lines.BUY_WORK, entity_ids=[call.me.id, work.id], me=call.me.name, work=work.name)
    return result(MortalResult.WORK_BOUGHT, work=work.name, price=sale.price)


async def found_club(call: MortalCall, args: FoundClubInput) -> str:
    town = await town_of(call.session, call.me)
    if town is None or held(town.id):
        fail(MortalResult.CLUB_DECLINED, why="you stand in no town")
    try:
        row = await arts.start_club(call.tick, town.id, args.kind)
    except ValidationFailedError as error:
        fail(MortalResult.CLUB_DECLINED, why=reason_of(error))
    call.target(row.faction_entity_id)
    await call.chronicle(ChronicleKind.CULTURE, lines.FOUND_CLUB, entity_ids=[call.me.id, town.id], me=call.me.name, town=town.name)
    return result(MortalResult.CLUB_FOUNDED, town=town.name, kind=row.kind.value.replace("_", " "))


async def take_contract(call: MortalCall, args: TakeContractInput) -> str:
    row = await call.session.get(MonsterContractRow, args.contract_id)
    if row is None or row.status is not ContractStatus.POSTED:
        fail(MortalResult.CONTRACT_DECLINED, why="no such contract is open")
    beast = await living_entity(call.session, row.beast_entity_id)
    if beast is None or beast.world_id != call.me.world_id:
        fail(MortalResult.CONTRACT_DECLINED, why="its quarry is beyond your world")
    if held(beast.id):
        fail(MortalResult.CONTRACT_DECLINED, why="a stronger hand holds its quarry")
    try:
        await constructs.assign_hunter(call.tick, row.id, call.me.id)
    except ValidationFailedError as error:
        fail(MortalResult.CONTRACT_DECLINED, why=reason_of(error))
    call.target(beast.id)
    await call.chronicle(ChronicleKind.WORLD, lines.TAKE_CONTRACT, entity_ids=[call.me.id, beast.id], me=call.me.name, beast=beast.name)
    return result(MortalResult.CONTRACT_TAKEN, beast=beast.name, bounty=row.bounty)


async def command_construct(call: MortalCall, args: CommandConstructInput) -> str:
    body = await living_entity(call.session, args.construct_id)
    if body is None or await call.session.get(ConstructRow, body.id) is None:
        fail(MortalResult.COMMAND_DECLINED, why="there is no such construct")
    if held(body.id):
        fail(MortalResult.COMMAND_DECLINED, why="a stronger hand holds it")
    rules = await constructs.rules_of(call.tick, body.id)
    if rules is None or await holder_of(call.tick, rules) != call.me.id:
        fail(MortalResult.COMMAND_DECLINED, why="you do not hold what commands it")
    target = await living_entity(call.session, args.target_id) if args.target_id is not None else None
    if args.target_id is not None and target is None:
        fail(MortalResult.COMMAND_DECLINED, why="there is no such target")
    await constructs.give_order(call.tick, rules.id, args.kind, target_id=args.target_id, priority=FIRST, condition=OrderCondition.ALWAYS, until_epoch=None)
    call.target(body.id)
    await call.chronicle(ChronicleKind.ORDER, lines.COMMAND_CONSTRUCT, entity_ids=[call.me.id, body.id], me=call.me.name, name=body.name, order=args.kind.value)
    return result(
        MortalResult.CONSTRUCT_COMMANDED, name=body.name, order=args.kind.value.replace("_", " "), target=target.name if target else "no one in particular"
    )


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.FORGE_WORK, mortal, ForgeWorkInput, meta, forge_work),
        ToolSpec(MortalToolId.BUY_WORK, mortal, BuyWorkInput, meta, buy_work),
        ToolSpec(MortalToolId.FOUND_CLUB, mortal, FoundClubInput, meta, found_club),
        ToolSpec(MortalToolId.TAKE_CONTRACT, mortal, TakeContractInput, meta, take_contract),
        ToolSpec(MortalToolId.COMMAND_CONSTRUCT, mortal, CommandConstructInput, meta, command_construct),
    ]
