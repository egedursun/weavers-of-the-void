from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.constants.units import PERCENT
from aerona.db.tables.space_weather import WorldFieldRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.recording.terms import explaining_alone, term
from aerona.engine.space_weather.weather import field_of
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.heavens import world_in_hand
from aerona.tools.son.support import require_essence

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class ShieldWorldInput(ToolInput):
    world_id: int
    change: Annotated[int, Field(ge=-PERCENT, le=PERCENT)]
    epochs: Annotated[int, Field(ge=1, le=50)]
    reason: Reason


async def shield_world(call: SonCall, args: ShieldWorldInput) -> str:
    world = await world_in_hand(call, args.world_id)
    if held(world.id):
        fail(SonResult.SHIELD_REFUSED, why="it is held")
    table = call.rules.space_weather
    if abs(args.change) > table.shield_change_max:
        fail(SonResult.SHIELD_REFUSED, why=f"no god moves a field by more than {table.shield_change_max} at once")
    cost = call.rules.son_tools.shield_world_essence
    require_essence(call, cost)
    field: WorldFieldRow = await field_of(call.tick, world)
    if "shift" in field.locked:
        fail(SonResult.SHIELD_REFUSED, why="this field is held")
    with explaining_alone():
        term("space_weather.shield", args.change, source_node_id=world.id)
        field.shift = clamp_int(args.change, -PERCENT, PERCENT)
        field.shift_left = args.epochs
    call.spend_essence(cost)
    call.target(world.id)
    await call.record(
        "tools.son.shield_world",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: world.id},
        facts={"change": args.change, "epochs": args.epochs, "reason": args.reason},
        kind=ChronicleKind.COSMIC,
    )
    return result(SonResult.WORLD_SHIELDED, world=world.name, field=clamp_int(world.magnetism + field.shift, 0, PERCENT), epochs=args.epochs)


def specs() -> list[ToolSpec[SonCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [ToolSpec(SonToolId.SHIELD_WORLD, AgentKind.SON, ShieldWorldInput, meta, shield_world)]
