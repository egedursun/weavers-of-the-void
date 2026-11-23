from typing import Any

from pydantic import Field
from sqlalchemy import select

from aerona.catalog.dominion import BARGAINING_MODES
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
from aerona.domain.enums.cycles import GiftOccasion, GiftState, LongPlanKind, ManumissionPath
from aerona.domain.enums.dominion import WorshipMode
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.structure import ConstructionStatus
from aerona.engine.cycles import control
from aerona.engine.cycles.gifts import OBLIGING, give, offer, refuse, release_gift_debt, return_gift
from aerona.engine.cycles.standing import node_name
from aerona.engine.demography.society_control import set_corvee
from aerona.engine.divine.standing import standing_row
from aerona.engine.economy.purse import take_coin
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

MANY = 1_000_000
NAME = 200
PLAN_STEPS = 100


class GiveGiftInput(ToolInput):
    receiver_id: int
    value: int = Field(ge=1, le=MANY)
    item_id: int | None = None
    occasion: GiftOccasion = GiftOccasion.COURTESY


class ReleaseDebtInput(ToolInput):
    gift_id: int


class GiftInput(ToolInput):
    gift_id: int
    value: int | None = Field(default=None, ge=0, le=MANY)


class RefuseGiftInput(ToolInput):
    gift_id: int


class OfferingInput(ToolInput):
    value: int = Field(ge=1, le=MANY)
    mode: WorshipMode | None = None


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
    gift = await give(call.tick, call.me.id, receiver.id, args.value, args.occasion, item_id=args.item_id, tell=True)
    if gift is None:
        fail(MortalResult.GIFT_REFUSED, why="you cannot afford it")
    call.target(receiver.id)
    await call.record(
        "tools.mortal.bestow_gift",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.RECEIVER: receiver.id},
        facts={"value": gift.value},
        kind=ChronicleKind.WORLD,
    )
    if gift.state is GiftState.REFUSED:
        return result(MortalResult.GIFT_SPURNED, name=receiver.name)
    if gift.state not in OBLIGING:
        return result(MortalResult.GIFT_FREE, name=receiver.name, value=gift.value, id=gift.id)
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
    await call.record("tools.mortal.answer_gift", roles={IncidentRole.ACTOR: call.me.id}, facts={"giver_detail": giver}, kind=ChronicleKind.WORLD)
    return result(MortalResult.GIFT_ANSWERED, name=giver, value=answer.value)


async def refuse_gift(call: MortalCall, args: RefuseGiftInput) -> str:
    gift = await owed_gift(call, args.gift_id)
    await refuse(call.tick, gift)
    giver = await node_name(call.session, gift.giver_node_id)
    await call.record("tools.mortal.refuse_gift", roles={IncidentRole.ACTOR: call.me.id}, facts={"giver_detail": giver}, kind=ChronicleKind.WORLD)
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
    if args.mode is not None and not held(home, god.id):
        standing = await standing_row(call.tick, home, god.id)
        if "mode" not in standing.locked:
            standing.mode = args.mode
        if args.mode in BARGAINING_MODES:
            await call.record("worship.bargain", roles={IncidentRole.SUBJECT: home, IncidentRole.PATRON: god.id}, facts={"answered": 0, "unanswered": 0})
    await call.record(
        "tools.mortal.make_offering",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: god.id},
        facts={"value": args.value},
        kind=ChronicleKind.WORLD,
    )
    return result(MortalResult.OFFERING_MADE, value=args.value, name=god.name, offered=row.offered, answered=row.answered)


async def free_bound(call: MortalCall, args: FreeBoundInput) -> str:
    realm = await ruled_realm(call)
    if realm is None:
        fail(MortalResult.BOUND_FREE_REFUSED, why="you rule no realm")
    town = await town_of_realm(call, realm, args.town_id, MortalResult.BOUND_FREE_REFUSED)
    row = await control.free_bound(call.tick, town.id, args.share, args.path)
    count = row.count if row is not None else 0
    call.target(town.id)
    await call.record(
        "tools.mortal.free_bound",
        roles={IncidentRole.AUTHORITY: realm.id, IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: town.id},
        facts={"freed": count, "share": args.share, "path": args.path},
        place=town.id,
    )
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
    await call.record(
        "tools.mortal.lay_corvee",
        roles={IncidentRole.AUTHORITY: call.me.id, IncidentRole.VICTIM: town.id, IncidentRole.SUBJECT: work.id},
        facts={"share": args.share},
        place=town.id,
    )
    return result(MortalResult.CORVEE_LAID, share=args.share, name=town.name, work=work.name)


async def release_debt(call: MortalCall, args: ReleaseDebtInput) -> str:
    gift = await call.session.get(GiftRow, args.gift_id)
    if gift is None or gift.giver_node_id != call.me.id or gift.state not in OBLIGING:
        fail(MortalResult.GIFT_ANSWER_REFUSED, why="nobody owes you a return for such a gift")
    if not await release_gift_debt(call.tick, gift):
        fail(MortalResult.GIFT_ANSWER_REFUSED, why="a god holds that gift")
    debtor = await node_name(call.session, gift.receiver_node_id)
    call.target(gift.receiver_node_id)
    await call.record("tools.mortal.release_debt", roles={IncidentRole.ACTOR: call.me.id}, facts={"debtor_detail": debtor}, kind=ChronicleKind.WORLD)
    return result(MortalResult.DEBT_RELEASED, name=debtor, value=gift.value)


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
    await call.record(
        "tools.mortal.begin_realm_plan",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.OWNER: realm.id},
        facts={"plan": plan.name, "plan_kind": plan.kind, "steps": plan.steps},
    )
    return result(MortalResult.REALM_PLAN_BEGUN, name=plan.name, id=plan.id)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.BESTOW_GIFT, mortal, GiveGiftInput, meta, bestow_gift),
        ToolSpec(MortalToolId.ANSWER_GIFT, mortal, GiftInput, meta, answer_gift),
        ToolSpec(MortalToolId.REFUSE_GIFT, mortal, RefuseGiftInput, meta, refuse_gift),
        ToolSpec(MortalToolId.RELEASE_DEBT, mortal, ReleaseDebtInput, meta, release_debt),
        ToolSpec(MortalToolId.MAKE_OFFERING, mortal, OfferingInput, meta, make_offering),
        ToolSpec(MortalToolId.FREE_BOUND, mortal, FreeBoundInput, meta, free_bound),
        ToolSpec(MortalToolId.LAY_CORVEE, mortal, CorveeInput, meta, lay_corvee),
        ToolSpec(MortalToolId.BEGIN_REALM_PLAN, mortal, RealmPlanInput, meta, begin_realm_plan),
    ]
