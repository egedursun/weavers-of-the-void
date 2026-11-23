from typing import Any

from sqlalchemy import select

from aerona.catalog.marks import MARKS
from aerona.catalog.revivals import REVIVAL_WAYS
from aerona.core.grammar import spoken
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.customs import CooperativeRow, MembershipRow, RevivalRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.customs import MarkKind, MarkMeaning, Membership, Naturalisation, RevivalGoal, RevivalWay
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.belonging.values import own_people
from aerona.engine.customs import control
from aerona.engine.customs.marks import MarkTally, place, unshown_augment
from aerona.engine.customs.revival import way_chosen
from aerona.engine.economy.purse import take_coin
from aerona.engine.primitives.queries import connect, living_entity
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail


class JoinCooperativeInput(ToolInput):
    faction_id: int


class SeekCitizenshipInput(ToolInput):
    pass


class LeadRevivalInput(ToolInput):
    people_id: int
    way: RevivalWay
    goal: RevivalGoal


class MarkBodyInput(ToolInput):
    kind: MarkKind
    meaning: MarkMeaning
    target_id: int | None = None


async def join_cooperative(call: MortalCall, args: JoinCooperativeInput) -> str:
    pool = await call.session.get(CooperativeRow, args.faction_id)
    faction = await living_entity(call.session, args.faction_id)
    if pool is None or faction is None:
        fail(MortalResult.COOPERATIVE_DECLINED, why="there is no such cooperative")
    if faction.location_id != call.me.location_id:
        fail(MortalResult.COOPERATIVE_DECLINED, why="it pools the means of another town")
    joined = await call.session.scalar(
        select(BondRow.id)
        .where(
            BondRow.source_node_id == call.me.id, BondRow.target_node_id == faction.id, BondRow.kind == BondKind.MEMBER_OF, BondRow.state == BondState.ACTIVE
        )
        .limit(1)
    )
    if joined is not None:
        fail(MortalResult.COOPERATIVE_DECLINED, why="your means are pooled there already")
    await connect(call.session, call.me.id, faction.id, BondKind.MEMBER_OF, call.tick.epoch, description="pooled their means")
    call.target(faction.id)
    await call.record(
        "tools.mortal.join_cooperative", roles={IncidentRole.MEMBER: call.me.id, IncidentRole.TARGET: faction.id}, facts={"purpose": pool.purpose}
    )
    return result(MortalResult.COOPERATIVE_JOINED, faction=faction.name, purpose=spoken(pool.purpose))


async def seek_citizenship(call: MortalCall, args: SeekCitizenshipInput) -> str:
    row = await call.session.get(MembershipRow, call.me.id)
    if row is None or row.category is not Membership.RESIDENT_FOREIGNER:
        fail(MortalResult.CITIZENSHIP_DECLINED, why="the realm does not count you a foreigner")
    if "category" in row.locked:
        fail(MortalResult.CITIZENSHIP_DECLINED, why="your standing is held")
    if not await take_coin(call.session, call.tick.rules, call.me, call.tick.rules.citizenship.purchase_cost):
        fail(MortalResult.CITIZENSHIP_DECLINED, why="you cannot pay the fee")
    row.category, row.path, row.since_epoch = Membership.CITIZEN, Naturalisation.PURCHASE, call.tick.epoch
    realm = await living_entity(call.session, row.polity_entity_id)
    call.target(call.me.id)
    await call.record(
        "tools.mortal.seek_citizenship",
        roles={IncidentRole.BUYER: call.me.id, IncidentRole.AUTHORITY: row.polity_entity_id},
        facts={"fee": call.tick.rules.citizenship.purchase_cost, "path": Naturalisation.PURCHASE},
    )
    return result(MortalResult.CITIZENSHIP_GRANTED, realm=realm.name if realm is not None else "the realm")


async def lead_revival(call: MortalCall, args: LeadRevivalInput) -> str:
    people = await living_entity(call.session, args.people_id)
    if people is None or people.entity_type is not EntityType.PEOPLE:
        fail(MortalResult.REVIVAL_DECLINED, why="there is no such people")
    if await own_people(call.session, call.me) != people.id:
        fail(MortalResult.REVIVAL_DECLINED, why="that people is not your own")
    if args.goal not in REVIVAL_WAYS[args.way].goals:
        fail(MortalResult.REVIVAL_DECLINED, why=f"a movement that will {spoken(args.way)} cannot seek to {spoken(args.goal)}")
    found = await call.session.scalar(select(RevivalRow).where(RevivalRow.people_entity_id == people.id, RevivalRow.ended_epoch.is_(None)).limit(1))
    if found is None:
        made = await control.set_record(
            call.tick,
            "revival",
            {},
            {"people_entity_id": people.id, "way": args.way, "goal": args.goal, "prophet_node_id": call.me.id, "started_epoch": call.tick.epoch},
        )
        row = made if isinstance(made, RevivalRow) else None
    elif {"way", "goal", "prophet_node_id"} & set(found.locked or []):
        fail(MortalResult.REVIVAL_DECLINED, why="the movement is held")
    else:
        found.way, found.goal, found.prophet_node_id = args.way, args.goal, call.me.id
        row = found
    if row is not None:
        await way_chosen(call.tick, row)
    call.target(people.id)
    await call.record(
        "tools.mortal.lead_revival",
        roles={IncidentRole.LEADER: call.me.id, IncidentRole.SUBJECT: people.id},
        facts={"way": args.way, "goal": args.goal},
    )
    return result(MortalResult.REVIVAL_LED, people=people.name, way=spoken(args.way), goal=spoken(args.goal))


async def mark_body(call: MortalCall, args: MarkBodyInput) -> str:
    bearer = call.me if args.target_id is None else await living_entity(call.session, args.target_id)
    if bearer is None or bearer.entity_type is not EntityType.MORTAL or bearer.location_id != call.me.location_id:
        fail(MortalResult.MARK_REFUSED, why="a mark goes only on yourself or on a mortal in your own place")
    if held(bearer.id):
        fail(MortalResult.MARK_REFUSED, why=f"{bearer.name} is held")
    augment = await unshown_augment(call.tick, bearer.id) if MARKS[args.kind].shows_augment else None
    if MARKS[args.kind].shows_augment and augment is None:
        fail(MortalResult.MARK_REFUSED, why=f"{bearer.name} carries no augment that is not shown already")
    await place(call.tick, bearer, args.kind, args.meaning, MarkTally(), augment_id=augment.id if augment is not None else None, told=False)
    call.target(bearer.id)
    await call.record(
        "tools.mortal.mark_body",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: bearer.id},
        facts={"kind": args.kind, "meaning": args.meaning},
        place=call.me.location_id,
    )
    return result(MortalResult.BODY_MARKED, own=bearer.id == call.me.id, name=bearer.name, kind=spoken(args.kind), meaning=spoken(args.meaning))


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.JOIN_COOPERATIVE, mortal, JoinCooperativeInput, meta, join_cooperative),
        ToolSpec(MortalToolId.SEEK_CITIZENSHIP, mortal, SeekCitizenshipInput, meta, seek_citizenship),
        ToolSpec(MortalToolId.LEAD_REVIVAL, mortal, LeadRevivalInput, meta, lead_revival),
        ToolSpec(MortalToolId.MARK_BODY, mortal, MarkBodyInput, meta, mark_body),
    ]
