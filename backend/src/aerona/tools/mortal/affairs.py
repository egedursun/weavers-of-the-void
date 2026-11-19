from typing import Any

from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import OfficeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.statecraft import CouncilTask, MandateKind
from aerona.engine.polity.mandates import issue
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.ruler import throne_of

TASK = "task"


class MandateInput(ToolInput):
    kind: MandateKind
    settlement_id: int | None = None
    commodity: CommodityKind | None = None
    district: DistrictKind | None = None
    amount: int = 0


class TaskInput(ToolInput):
    office_id: int
    task: CouncilTask
    target_id: int | None = None


async def issue_mandate(call: MortalCall, args: MandateInput) -> str:
    realm = await throne_of(call)
    place = await call.session.get(EntityRow, args.settlement_id) if args.settlement_id is not None else None
    if args.settlement_id is not None and (place is None or place.entity_type is not EntityType.SETTLEMENT):
        fail(MortalResult.MANDATE_REFUSED, why="a mandate is laid on a settlement")
    if args.kind is MandateKind.EXPORT_BAN and args.commodity is None:
        fail(MortalResult.MANDATE_REFUSED, why="name the good whose export you ban")
    if args.kind is MandateKind.BUILD and args.district is None:
        fail(MortalResult.MANDATE_REFUSED, why="name the quarter to be built")
    row = await issue(
        call.tick, realm, args.kind, settlement_id=args.settlement_id, commodity=args.commodity, district=args.district, amount=max(0, args.amount)
    )
    if row is None:
        fail(MortalResult.MANDATE_REFUSED, why="such a mandate already stands, or a god holds the realm")
    kind = spoken(args.kind)
    call.target(place.id if place is not None else realm.entity.id)
    await call.record(
        "tools.mortal.mandate",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.AUTHORITY: realm.entity.id, IncidentRole.SUBJECT: place.id if place is not None else None},
        facts={"mandate": args.kind, "until": row.until_epoch},
    )
    return result(MortalResult.MANDATE_ISSUED, kind=kind, until=row.until_epoch)


async def assign_task(call: MortalCall, args: TaskInput) -> str:
    realm = await throne_of(call)
    office = await call.session.get(OfficeRow, args.office_id)
    if office is None or office.polity_entity_id != realm.entity.id:
        fail(MortalResult.TASK_REFUSED, why="that office is not of your realm")
    if TASK in (office.locked or []):
        fail(MortalResult.TASK_REFUSED, why="a god holds that office's task")
    office.task = args.task
    office.task_target_node_id = args.target_id
    await call.session.flush()
    task = spoken(args.task)
    call.target(realm.entity.id)
    await call.record(
        "tools.mortal.task",
        roles={IncidentRole.AUTHORITY: realm.entity.id, IncidentRole.ACTOR: call.me.id, IncidentRole.TARGET: args.target_id},
        facts={"office": office.kind, "task": args.task},
    )
    return result(MortalResult.TASK_SET, office=spoken(office.kind), task=task)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.ISSUE_MANDATE, AgentKind.MORTAL, MandateInput, meta, issue_mandate),
        ToolSpec(MortalToolId.ASSIGN_TASK, AgentKind.MORTAL, TaskInput, meta, assign_task),
    ]
