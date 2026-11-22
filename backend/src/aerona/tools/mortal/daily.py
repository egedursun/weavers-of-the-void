from typing import Any

from pydantic import Field
from sqlalchemy import delete, select

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.daily_life import DomesticServiceRow, HouseworkRow, LeisurePursuitRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.households import HouseholdMemberRow, HouseholdRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.daily_life import HouseDuty, LeisureKind, ServiceTerms
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.genetics import HouseholdRole
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.daily.service import willing_servant
from aerona.engine.households.formation import join_household
from aerona.engine.primitives.numbers import clamp_int
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

DECIDERS = frozenset({HouseholdRole.HEAD, HouseholdRole.SPOUSE})
DUTIES_MAX = len(HouseDuty)


class HireServantInput(ToolInput):
    household_id: int
    terms: ServiceTerms = ServiceTerms.WAGE
    wage: int = Field(default=0, ge=0)
    duties: list[HouseDuty] = Field(default_factory=list, max_length=DUTIES_MAX)


class TakeLeisureInput(ToolInput):
    kind: LeisureKind
    venue_id: int | None = None


class DutyAssignment(ToolInput):
    member_id: int
    duty: HouseDuty


class SetHouseDutiesInput(ToolInput):
    household_id: int
    assignments: list[DutyAssignment] = Field(min_length=1, max_length=DUTIES_MAX * 4)


async def ruled_household(call: MortalCall, household_id: int) -> HouseholdRow:
    household = await call.session.get(HouseholdRow, household_id)
    member = await call.session.get(HouseholdMemberRow, call.me.id)
    if household is None or member is None or member.household_id != household.id:
        fail(MortalResult.DAILY_REFUSED, why="you belong to no such household")
    if member.role not in DECIDERS:
        fail(MortalResult.DAILY_REFUSED, why="only the head of a household or their spouse decides for it")
    if held(household.head_node_id):
        fail(MortalResult.DAILY_REFUSED, why="a god holds your household as it is")
    return household


async def hire_servant(call: MortalCall, args: HireServantInput) -> str:
    household = await ruled_household(call, args.household_id)
    if args.terms is ServiceTerms.WAGE and household.wealth < args.wage:
        fail(MortalResult.DAILY_REFUSED, why="your household cannot pay that wage")
    servant = await willing_servant(call.session, household, call.me.id)
    if servant is None:
        fail(MortalResult.DAILY_REFUSED, why="no one in your town is free to enter service")
    call.session.add(
        DomesticServiceRow(servant_node_id=servant.id, household_id=household.id, terms=args.terms, wage=args.wage, since_epoch=call.epoch, locked=[])
    )
    await join_household(call.tick, household, servant, HouseholdRole.SERVANT)
    load = PERCENT // DUTIES_MAX
    for duty in dict.fromkeys(args.duties):
        call.session.add(HouseworkRow(household_id=household.id, duty=duty, doer_node_id=servant.id, doer_role=HouseholdRole.SERVANT, load=load, locked=[]))
    household.servants += 1
    call.target(servant.id)
    await call.record(
        "daily.servant_hired",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: servant.id},
        facts={"terms": args.terms, "wage": args.wage},
        place=household.settlement_node_id,
    )
    return result(MortalResult.SERVANT_HIRED, servant=servant.name, household=household.name, duties=len(dict.fromkeys(args.duties)))


async def take_leisure(call: MortalCall, args: TakeLeisureInput) -> str:
    venue = await call.session.get(EntityRow, args.venue_id) if args.venue_id is not None else None
    if args.venue_id is not None and (venue is None or venue.status is not EntityStatus.CANON):
        fail(MortalResult.DAILY_REFUSED, why="there is no such place to go")
    profile = await call.session.get(MortalProfileRow, call.me.id)
    if profile is None:
        fail(MortalResult.DAILY_REFUSED, why="you have no life of your own to spend")
    table = call.rules.daily_life
    pursuit = await call.session.scalar(select(LeisurePursuitRow).where(LeisurePursuitRow.holder_node_id == call.me.id, LeisurePursuitRow.kind == args.kind))
    if pursuit is None:
        pursuit = LeisurePursuitRow(holder_node_id=call.me.id, kind=args.kind, share=0, locked=[])
        call.session.add(pursuit)
    pursuit.share = clamp_int(pursuit.share + table.leisure_happiness_pct, 0, PERCENT)
    pursuit.venue_node_id = venue.id if venue is not None else pursuit.venue_node_id
    if "mood_score" not in (profile.locked or []):
        profile.mood_score = clamp_int(profile.mood_score + table.leisure_happiness_pct, -PERCENT, PERCENT)
    if "stress" not in (profile.locked or []):
        profile.stress = clamp_int(profile.stress - table.leisure_happiness_pct, 0, PERCENT)
    call.target(call.me.id)
    await call.record(
        "tools.mortal.leisure_taken",
        roles={IncidentRole.ACTOR: call.me.id, **({IncidentRole.PLACE: venue.id} if venue is not None else {})},
        facts={"pursuit": args.kind},
        place=venue.id if venue is not None else call.me.location_id,
    )
    return result(MortalResult.LEISURE_TAKEN, pursuit=spoken(args.kind), mood=profile.mood_score)


async def set_house_duties(call: MortalCall, args: SetHouseDutiesInput) -> str:
    household = await ruled_household(call, args.household_id)
    members = {
        member.member_node_id: member.role
        for member in await call.session.scalars(select(HouseholdMemberRow).where(HouseholdMemberRow.household_id == household.id))
    }
    servants = set(await call.session.scalars(select(DomesticServiceRow.servant_node_id).where(DomesticServiceRow.household_id == household.id)))
    outsiders = sorted({item.member_id for item in args.assignments} - set(members) - servants)
    if outsiders:
        fail(MortalResult.DAILY_REFUSED, why="a duty can go only to a member or a servant of your household")
    await call.session.execute(delete(HouseworkRow).where(HouseworkRow.household_id == household.id))
    pairs = list(dict.fromkeys((item.member_id, item.duty) for item in args.assignments))
    load = PERCENT // max(1, len(pairs))
    for member_id, duty in pairs:
        role = members.get(member_id, HouseholdRole.SERVANT)
        call.session.add(HouseworkRow(household_id=household.id, duty=duty, doer_node_id=member_id, doer_role=role, load=load, locked=[]))
    call.target(call.me.id)
    await call.record(
        "tools.mortal.house_duties_set",
        roles={IncidentRole.ACTOR: call.me.id},
        facts={"household": household.name, "duties": len(pairs)},
        place=household.settlement_node_id,
    )
    return result(MortalResult.HOUSE_DUTIES_SET, household=household.name, duties=len(pairs))


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [
        ToolSpec(MortalToolId.HIRE_SERVANT, AgentKind.MORTAL, HireServantInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), hire_servant),
        ToolSpec(MortalToolId.TAKE_LEISURE, AgentKind.MORTAL, TakeLeisureInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), take_leisure),
        ToolSpec(
            MortalToolId.SET_HOUSE_DUTIES, AgentKind.MORTAL, SetHouseDutiesInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), set_house_duties
        ),
    ]
