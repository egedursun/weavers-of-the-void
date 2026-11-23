from typing import Annotated, Any

from pydantic import Field

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.tables.constructs import ConstructRow
from aerona.db.tables.contracts import MonsterContractRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.arts import ClubKind, ForgeryKind
from aerona.domain.enums.constructs import ContractStatus, OrderCondition, OrderKind
from aerona.domain.enums.crafts import RightKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.arts import control as arts
from aerona.engine.constructs import control as constructs
from aerona.engine.constructs.orders import holder_of
from aerona.engine.crafts import control as crafts
from aerona.engine.cycles.standing import node_name
from aerona.engine.primitives.queries import living_entity
from aerona.engine.sacred.places import town_of
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

FIRST = 1


class ForgeWorkInput(ToolInput):
    original_id: int
    kind: ForgeryKind | None = None


class ReviewWorkInput(ToolInput):
    artwork_id: int


class ClaimRightInput(ToolInput):
    kind: RightKind
    name: Annotated[str, Field(min_length=1, max_length=NAME_MAX_LENGTH)]
    subject_id: int | None = None
    dish_id: int | None = None
    technique: Technique | None = None
    contest_id: int | None = None
    marriage_id: int | None = None


class BuyWorkInput(ToolInput):
    artwork_id: int


class FoundClubInput(ToolInput):
    kind: ClubKind | None = None


class FixContestInput(ToolInput):
    match_id: int
    side: int


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
        row = await arts.forge_work(call.tick, original.id, call.me.id, args.kind)
    except ValidationFailedError as error:
        fail(MortalResult.FORGERY_DECLINED, why=reason_of(error))
    call.target(row.item_entity_id)
    await call.record(
        "tools.mortal.forge_work",
        roles={IncidentRole.MAKER: call.me.id, IncidentRole.SUBJECT: original.id, IncidentRole.PRODUCT: row.item_entity_id},
        facts={"forgery": row.kind, "skill": row.skill},
    )
    return result(MortalResult.FORGERY_MADE, original=original.name, kind=spoken(row.kind), skill=row.skill)


async def review_work(call: MortalCall, args: ReviewWorkInput) -> str:
    try:
        verdict = await arts.review_work(call.tick, args.artwork_id, call.me.id)
    except ValidationFailedError as error:
        fail(MortalResult.REVIEW_DECLINED, why=reason_of(error))
    call.target(args.artwork_id)
    await call.record("tools.mortal.review_work", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: args.artwork_id}, facts={"acclaim": verdict})
    return result(MortalResult.WORK_REVIEWED, work=await node_name(call.session, args.artwork_id), acclaim=verdict)


async def claim_right(call: MortalCall, args: ClaimRightInput) -> str:
    try:
        row = await crafts.claim_right(
            call.tick,
            call.me.id,
            args.kind,
            args.name,
            subject_id=args.subject_id,
            dish_id=args.dish_id,
            technique=args.technique,
            contest_id=args.contest_id,
            marriage_id=args.marriage_id,
        )
    except ValidationFailedError as error:
        fail(MortalResult.RIGHT_DECLINED, why=reason_of(error))
    await call.record("tools.mortal.claim_right", roles={IncidentRole.OWNER: call.me.id}, facts={"right": row.name, "kind": row.kind, "way": row.acquired})
    return result(MortalResult.RIGHT_CLAIMED, name=row.name, kind=spoken(row.kind), way=spoken(row.acquired))


async def buy_work(call: MortalCall, args: BuyWorkInput) -> str:
    work = await living_entity(call.session, args.artwork_id)
    if work is None or held(work.id):
        fail(MortalResult.PURCHASE_DECLINED, why="there is no such work")
    try:
        sale = await arts.sell_work(call.tick, work.id, call.me.id, None)
    except ValidationFailedError as error:
        fail(MortalResult.PURCHASE_DECLINED, why=reason_of(error))
    call.target(work.id)
    await call.record("tools.mortal.buy_work", roles={IncidentRole.BUYER: call.me.id, IncidentRole.SUBJECT: work.id}, facts={"price": sale.price})
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
    await call.record(
        "tools.mortal.found_club",
        roles={IncidentRole.LEADER: call.me.id, IncidentRole.PRODUCT: row.faction_entity_id, IncidentRole.PLACE: town.id},
        facts={"game": row.kind},
        place=town.id,
    )
    return result(MortalResult.CLUB_FOUNDED, town=town.name, kind=spoken(row.kind))


async def fix_contest(call: MortalCall, args: FixContestInput) -> str:
    try:
        club = await arts.fix_contest(call.tick, call.me.id, args.match_id, args.side)
    except ValidationFailedError as error:
        fail(MortalResult.FIXING_DECLINED, why=reason_of(error))
    call.target(club.faction_entity_id)
    await call.record("tools.mortal.fix_contest", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.BENEFICIARY: club.faction_entity_id})
    return result(MortalResult.FIXING_ARRANGED, club=await node_name(call.session, club.faction_entity_id))


async def take_contract(call: MortalCall, args: TakeContractInput) -> str:
    row = await call.session.get(MonsterContractRow, args.contract_id)
    if row is None or row.status is not ContractStatus.POSTED:
        fail(MortalResult.CONTRACT_DECLINED, why="no such contract is open")
    beast = await living_entity(call.session, row.beast_entity_id)
    if beast is None or beast.world_id != call.me.world_id:
        fail(MortalResult.CONTRACT_DECLINED, why="its quarry is beyond your world")
    if held(beast.id):
        fail(MortalResult.CONTRACT_DECLINED, why="its quarry is held")
    try:
        await constructs.assign_hunter(call.tick, row.id, call.me.id)
    except ValidationFailedError as error:
        fail(MortalResult.CONTRACT_DECLINED, why=reason_of(error))
    call.target(beast.id)
    await call.record("tools.mortal.take_contract", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.TARGET: beast.id}, facts={"bounty": row.bounty})
    return result(MortalResult.CONTRACT_TAKEN, beast=beast.name, bounty=row.bounty)


async def command_construct(call: MortalCall, args: CommandConstructInput) -> str:
    body = await living_entity(call.session, args.construct_id)
    if body is None or await call.session.get(ConstructRow, body.id) is None:
        fail(MortalResult.COMMAND_DECLINED, why="there is no such construct")
    if held(body.id):
        fail(MortalResult.COMMAND_DECLINED, why="it is held")
    rules = await constructs.rules_of(call.tick, body.id)
    if rules is None or await holder_of(call.tick, rules) != call.me.id:
        fail(MortalResult.COMMAND_DECLINED, why="you do not hold what commands it")
    target = await living_entity(call.session, args.target_id) if args.target_id is not None else None
    if args.target_id is not None and target is None:
        fail(MortalResult.COMMAND_DECLINED, why="there is no such target")
    await constructs.give_order(call.tick, rules.id, args.kind, target_id=args.target_id, priority=FIRST, condition=OrderCondition.ALWAYS, until_epoch=None)
    call.target(body.id)
    await call.record(
        "tools.mortal.command_construct",
        roles={IncidentRole.AUTHORITY: call.me.id, IncidentRole.SUBJECT: body.id, IncidentRole.TARGET: target.id if target is not None else None},
        facts={"order": args.kind},
    )
    return result(MortalResult.CONSTRUCT_COMMANDED, name=body.name, order=spoken(args.kind), target=target.name if target else "no one in particular")


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.FORGE_WORK, mortal, ForgeWorkInput, meta, forge_work),
        ToolSpec(MortalToolId.BUY_WORK, mortal, BuyWorkInput, meta, buy_work),
        ToolSpec(MortalToolId.REVIEW_WORK, mortal, ReviewWorkInput, meta, review_work),
        ToolSpec(MortalToolId.CLAIM_RIGHT, mortal, ClaimRightInput, meta, claim_right),
        ToolSpec(MortalToolId.FOUND_CLUB, mortal, FoundClubInput, meta, found_club),
        ToolSpec(MortalToolId.FIX_CONTEST, mortal, FixContestInput, meta, fix_contest),
        ToolSpec(MortalToolId.TAKE_CONTRACT, mortal, TakeContractInput, meta, take_contract),
        ToolSpec(MortalToolId.COMMAND_CONSTRUCT, mortal, CommandConstructInput, meta, command_construct),
    ]
