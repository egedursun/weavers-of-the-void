from typing import Any

from pydantic import Field
from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.cycles import GiftRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.db.tables.structures import ConstructionRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.cycles import GiftOccasion, LongPlanKind, ManumissionPath
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.structure import ConstructionStatus
from aerona.engine.cycles import control
from aerona.engine.cycles.gifts import OBLIGING, give, offer, refuse, return_gift
from aerona.engine.cycles.standing import node_name
from aerona.engine.demography.society_control import set_corvee
from aerona.engine.economy.purse import take_coin
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal import lines

MANY = 1_000_000
NAME = 200
PLAN_STEPS = 100


class GiveGiftInput(ToolInput):
    receiver_id: int
    value: int = Field(ge=1, le=MANY)
    item_id: int | None = None


class GiftInput(ToolInput):
    gift_id: int
    value: int | None = Field(default=None, ge=0, le=MANY)


class RefuseGiftInput(ToolInput):
    gift_id: int


class OfferingInput(ToolInput):
    value: int = Field(ge=1, le=MANY)


class FreeBoundInput(ToolInput):
    town_id: int
    share: int = Field(ge=1, le=PERCENT)
    path: ManumissionPath


class CorveeInput(ToolInput):
    town_id: int
    work_id: int
    share: int = Field(ge=0, le=PERCENT)


class RealmPlanInput(ToolInput):
    kind: LongPlanKind
    name: str = Field(min_length=1, max_length=NAME)
    target_id: int | None = None
    steps: int = Field(default=10, ge=1, le=PLAN_STEPS)
    secrecy: int = Field(default=50, ge=0, le=PERCENT)


async def ruled_realm(call: MortalCall) -> EntityRow | None:
    realm_id = await call.session.scalar(
        select(OfficeRow.polity_entity_id).where(OfficeRow.holder_entity_id == call.me.id, OfficeRow.kind == OfficeKind.RULER).limit(1)
    )
    return await living_entity(call.session, realm_id) if realm_id is not None else None


async def town_of_realm(call: MortalCall, realm: EntityRow, town_id: int, refused: MortalResult) -> EntityRow:
    member = await call.session.get(PolityMemberRow, (realm.id, town_id))
    town = await living_entity(call.session, town_id)
    if member is None or town is None:
        fail(refused, why="that town is not of your realm")
    if held(town.id):
        fail(refused, why="a god holds that town")
    return town


async def bestow_gift(call: MortalCall, args: GiveGiftInput) -> str:
    receiver = await living_entity(call.session, args.receiver_id)
    if receiver is None or receiver.id == call.me.id:
        fail(MortalResult.GIFT_REFUSED, why="there is nobody of that name to give to")
    if args.item_id is not None and await call.session.get(EntityRow, args.item_id) is None:
        fail(MortalResult.GIFT_REFUSED, why="you hold no such thing")
    gift = await give(call.tick, call.me.id, receiver.id, args.value, GiftOccasion.COURTESY, item_id=args.item_id)
    if gift is None:
        fail(MortalResult.GIFT_REFUSED, why="you cannot afford it")
    call.target(receiver.id)
    await call.chronicle(
        ChronicleKind.WORLD, lines.BESTOW_GIFT, entity_ids=[call.me.id, receiver.id], me=call.me.name, receiver=receiver.name, value=gift.value
    )
    if gift.state not in OBLIGING:
        return result(MortalResult.GIFT_SPURNED, name=receiver.name)
    return result(MortalResult.GIFT_GIVEN, name=receiver.name, value=gift.value, id=gift.id, due=gift.due_epoch)


async def owed_gift(call: MortalCall, gift_id: int) -> GiftRow:
    gift = await call.session.get(GiftRow, gift_id)
    if gift is None or gift.receiver_node_id != call.me.id or gift.state not in OBLIGING:
        fail(MortalResult.GIFT_ANSWER_REFUSED, why="you owe no such gift")
    return gift


async def answer_gift(call: MortalCall, args: GiftInput) -> str:
    gift = await owed_gift(call, args.gift_id)
    answer = await return_gift(call.tick, gift, value=args.value)
    if answer is None:
        fail(MortalResult.GIFT_ANSWER_REFUSED, why="you cannot afford to answer it")
    giver = await node_name(call.session, gift.giver_node_id)
    await call.chronicle(ChronicleKind.WORLD, lines.ANSWER_GIFT, entity_ids=[call.me.id], me=call.me.name, giver=giver)
    return result(MortalResult.GIFT_ANSWERED, name=giver, value=answer.value)


async def refuse_gift(call: MortalCall, args: RefuseGiftInput) -> str:
    gift = await owed_gift(call, args.gift_id)
    await refuse(call.tick, gift)
    giver = await node_name(call.session, gift.giver_node_id)
    await call.chronicle(ChronicleKind.WORLD, lines.REFUSE_GIFT, entity_ids=[call.me.id], me=call.me.name, giver=giver)
    return result(MortalResult.GIFT_DECLINED, name=giver)


async def make_offering(call: MortalCall, args: OfferingInput) -> str:
    god = await living_patron(call.session, call.me)
    home = call.me.location_id
    if god is None or home is None:
        fail(MortalResult.OFFERING_REFUSED, why="you worship no god, or have no home to offer from")
    if not await take_coin(call.session, call.tick.rules, call.me, args.value):
        fail(MortalResult.OFFERING_REFUSED, why="you cannot afford it")
    await give(call.tick, call.me.id, god.id, args.value, GiftOccasion.OFFERING, pay=False)
    row = await offer(call.tick, home, god.id, args.value)
    await call.chronicle(ChronicleKind.WORLD, lines.MAKE_OFFERING, entity_ids=[call.me.id], me=call.me.name, value=args.value, god=god.name)
    return result(MortalResult.OFFERING_MADE, value=args.value, name=god.name, offered=row.offered, answered=row.answered)


async def free_bound(call: MortalCall, args: FreeBoundInput) -> str:
    realm = await ruled_realm(call)
    if realm is None:
        fail(MortalResult.BOUND_FREE_REFUSED, why="you rule no realm")
    town = await town_of_realm(call, realm, args.town_id, MortalResult.BOUND_FREE_REFUSED)
    row = await control.free_bound(call.tick, town.id, args.share, args.path)
    count = row.count if row is not None else 0
    call.target(town.id)
    await call.chronicle(ChronicleKind.WORLD, lines.FREE_BOUND, entity_ids=[call.me.id, town.id], me=call.me.name, count=count, town=town.name)
    return result(MortalResult.BOUND_FREED, count=count, name=town.name)


async def lay_corvee(call: MortalCall, args: CorveeInput) -> str:
    realm = await ruled_realm(call)
    if realm is None:
        fail(MortalResult.CORVEE_REFUSED, why="you rule no realm")
    town = await town_of_realm(call, realm, args.town_id, MortalResult.CORVEE_REFUSED)
    raising = await call.session.scalar(
        select(ConstructionRow).where(ConstructionRow.structure_entity_id == args.work_id, ConstructionRow.status == ConstructionStatus.ACTIVE).limit(1)
    )
    work = await call.session.get(EntityRow, args.work_id)
    if raising is None or work is None:
        fail(MortalResult.CORVEE_REFUSED, why="that work is not being raised")
    if raising.site_entity_id is None or await call.session.get(PolityMemberRow, (realm.id, raising.site_entity_id)) is None:
        fail(MortalResult.CORVEE_REFUSED, why="that work is not raised in your realm")
    await set_corvee(call.tick, town.id, args.share, realm.id, work.id if args.share > 0 else None)
    call.target(town.id)
    await call.chronicle(ChronicleKind.WORLD, lines.LAY_CORVEE, entity_ids=[call.me.id, town.id, work.id], me=call.me.name, town=town.name, work=work.name)
    return result(MortalResult.CORVEE_LAID, share=args.share, name=town.name, work=work.name)


async def begin_realm_plan(call: MortalCall, args: RealmPlanInput) -> str:
    realm = await ruled_realm(call)
    if realm is None or held(realm.id):
        fail(MortalResult.REALM_PLAN_REFUSED, why="you rule no realm")
    try:
        plan = await control.new_plan(
            call.tick,
            realm.id,
            args.kind,
            args.name,
            target_id=args.target_id,
            carrier_id=call.me.id,
            steps=args.steps,
            step_cost=call.tick.rules.long_plans.default_cost,
            secrecy=args.secrecy,
        )
    except ValidationFailedError as error:
        fail(MortalResult.REALM_PLAN_REFUSED, why=str(error).rstrip("."))
    await call.chronicle(ChronicleKind.WORLD, lines.BEGIN_REALM_PLAN, entity_ids=[call.me.id, realm.id], me=call.me.name, realm=realm.name, plan=plan.name)
    return result(MortalResult.REALM_PLAN_BEGUN, name=plan.name, id=plan.id)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.BESTOW_GIFT, mortal, GiveGiftInput, meta, bestow_gift),
        ToolSpec(MortalToolId.ANSWER_GIFT, mortal, GiftInput, meta, answer_gift),
        ToolSpec(MortalToolId.REFUSE_GIFT, mortal, RefuseGiftInput, meta, refuse_gift),
        ToolSpec(MortalToolId.MAKE_OFFERING, mortal, OfferingInput, meta, make_offering),
        ToolSpec(MortalToolId.FREE_BOUND, mortal, FreeBoundInput, meta, free_bound),
        ToolSpec(MortalToolId.LAY_CORVEE, mortal, CorveeInput, meta, lay_corvee),
        ToolSpec(MortalToolId.BEGIN_REALM_PLAN, mortal, RealmPlanInput, meta, begin_realm_plan),
    ]
