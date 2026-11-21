from typing import Any

from pydantic import Field

from aerona.core.grammar import spoken
from aerona.db.tables.departures import DepartureRow
from aerona.db.tables.governance import OrgGovernanceRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.departures import DepartureCondition, DepartureKind
from aerona.engine.departures.book import Seat
from aerona.engine.departures.leave import leave
from aerona.engine.departures.returns import return_to, weak_seat
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

CONDITIONS_MAX = 4


class LeaveOfficeInput(ToolInput):
    office_id: int | None = None
    org_id: int | None = None
    kind: DepartureKind
    in_favour_of_id: int | None = None
    conditions: list[DepartureCondition] = Field(default_factory=list, max_length=CONDITIONS_MAX)


class ReturnToOfficeInput(ToolInput):
    departure_id: int


async def my_seat(call: MortalCall, args: LeaveOfficeInput) -> Seat:
    if (args.office_id is None) == (args.org_id is None):
        fail(MortalResult.DEPARTURE_REFUSED, why="name either the office of a realm or the organisation you head, and only one")
    if args.office_id is not None:
        office = await call.session.get(OfficeRow, args.office_id)
        if office is None or office.holder_entity_id != call.me.id:
            fail(MortalResult.DEPARTURE_REFUSED, why="you do not hold that office")
        if held(office.polity_entity_id) or "holder_entity_id" in (office.locked or []):
            fail(MortalResult.DEPARTURE_REFUSED, why="a god holds that office as it is")
        return Seat(call.me, office, None)
    org = await call.session.get(OrgGovernanceRow, args.org_id)
    if org is None or org.head_node_id != call.me.id:
        fail(MortalResult.DEPARTURE_REFUSED, why="you do not head that organisation")
    if held(org.org_node_id) or "head_node_id" in (org.locked or []):
        fail(MortalResult.DEPARTURE_REFUSED, why="a god holds that headship as it is")
    return Seat(call.me, None, org)


async def leave_office_tool(call: MortalCall, args: LeaveOfficeInput) -> str:
    seat = await my_seat(call, args)
    if args.in_favour_of_id is not None and held(args.in_favour_of_id):
        fail(MortalResult.DEPARTURE_REFUSED, why="a god holds the one you would hand it to")
    row = await leave(call.tick, seat, args.kind, heir=args.in_favour_of_id, conditions=list(args.conditions), why="by their own choice")
    call.target(row.polity_entity_id or row.org_node_id)
    successor = await call.session.get(type(call.me), row.in_favour_of_node_id) if row.in_favour_of_node_id is not None else None
    return result(MortalResult.OFFICE_LEFT, kind=spoken(row.kind), successor=successor.name if successor is not None else "no one yet")


async def return_to_office_tool(call: MortalCall, args: ReturnToOfficeInput) -> str:
    row = await call.session.get(DepartureRow, args.departure_id)
    if row is None or row.holder_node_id != call.me.id or row.returned_epoch is not None:
        fail(MortalResult.DEPARTURE_REFUSED, why="you left no such office that you have not already come back to")
    if row.kind is DepartureKind.RETIREMENT:
        fail(MortalResult.DEPARTURE_REFUSED, why="one who retired does not come back")
    if not await weak_seat(call.tick, row):
        fail(MortalResult.DEPARTURE_REFUSED, why="the office is held firmly by another")
    if not await return_to(call.tick, row, call.me):
        fail(MortalResult.DEPARTURE_REFUSED, why="a god holds that office as it is")
    call.target(row.polity_entity_id or row.org_node_id)
    return result(MortalResult.OFFICE_RETURNED, kind=spoken(row.kind))


def specs() -> list[ToolSpec[MortalCall, Any]]:
    act = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.LEAVE_OFFICE, AgentKind.MORTAL, LeaveOfficeInput, act, leave_office_tool),
        ToolSpec(MortalToolId.RETURN_TO_OFFICE, AgentKind.MORTAL, ReturnToOfficeInput, act, return_to_office_tool),
    ]
