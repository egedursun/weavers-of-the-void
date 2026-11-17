from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.prehistory import EPOCHS_MAX
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.prehistory.control import seed
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import require_essence

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class PlanPrehistoryInput(ToolInput):
    world_id: int
    epochs: int = Field(ge=1, le=EPOCHS_MAX)
    reason: Reason


async def plan_prehistory(call: SonCall, args: PlanPrehistoryInput) -> str:
    world = await call.session.get(WorldRow, args.world_id)
    if world is None or world.creator_son_id != call.son.id:
        fail(SonResult.PREHISTORY_REFUSED, why="you can give a past only to a world you made")
    if held(world.id):
        fail(SonResult.PREHISTORY_REFUSED, why="a stronger hand holds that world")
    cost = call.rules.prehistory.son_seed_cost
    require_essence(call, cost)
    try:
        await seed(call.tick, world.id, args.epochs, call.rules.prehistory.resolution)
    except ValidationFailedError as error:
        fail(SonResult.PREHISTORY_REFUSED, why=str(error).rstrip("."))
    call.spend_essence(cost)
    call.target(world.id)
    await call.record(
        "tools.son.plan_prehistory",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: world.id},
        facts={"epochs": args.epochs, "reason": args.reason},
        kind=ChronicleKind.DIVINE_SIGN,
    )
    return result(SonResult.PREHISTORY_PLANNED, world=world.name, epochs=args.epochs)


def specs() -> list[ToolSpec[SonCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [ToolSpec(SonToolId.PLAN_PREHISTORY, AgentKind.SON, PlanPrehistoryInput, meta, plan_prehistory)]
