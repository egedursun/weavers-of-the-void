from typing import Annotated, Any

from pydantic import Field

from aerona.catalog.transformations import TRANSFORMS
from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NodeRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.transform import TransformKind, TransformTrigger
from aerona.engine.transform.run import press
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach, require_essence

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class PressTransformationInput(ToolInput):
    kind: TransformKind
    subject_id: int
    reason: Reason


async def press_transformation(call: SonCall, args: PressTransformationInput) -> str:
    node = await call.session.get(NodeRow, args.subject_id)
    if node is None:
        fail(SonResult.TRANSFORMATION_REFUSED, why="there is no such thing")
    if held(node.id):
        fail(SonResult.TRANSFORMATION_REFUSED, why="a stronger hand holds it")
    entity = await call.session.get(EntityRow, node.id)
    if entity is not None:
        await ensure_in_reach(call, entity)
    cost = call.rules.transform.press_cost
    require_essence(call, cost)
    try:
        row = await press(call.tick, args.kind, node.id, call.rules.transform.press_amount, TransformTrigger.SON)
    except ValidationFailedError as error:
        fail(SonResult.TRANSFORMATION_REFUSED, why=str(error).rstrip("."))
    call.spend_essence(cost)
    call.target(node.id)
    change = TRANSFORMS[args.kind].label.lower()
    await call.record(
        "tools.son.press_transformation",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: node.id},
        facts={"change": change, "reason": args.reason},
        kind=ChronicleKind.DIVINE_SIGN,
    )
    return result(SonResult.TRANSFORMATION_PRESSED, subject=node.name, change=change, progress=row.progress)


def specs() -> list[ToolSpec[SonCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [ToolSpec(SonToolId.PRESS_TRANSFORMATION, AgentKind.SON, PressTransformationInput, meta, press_transformation)]
