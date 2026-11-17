from typing import Annotated, Any, Literal

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.db.tables.world_views import SHARE_MAX, WORLD_VIEW_SHARES
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.cosmos.world_view_control import edit_view
from aerona.engine.cosmos.world_views import seed_view
from aerona.engine.primitives.numbers import clamp_int
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.ages import world_in_reach
from aerona.tools.son.support import require_essence

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
Share = Literal["timber_pct", "food_need_pct", "capacity_pct", "ore_yield_pct", "storm_pct", "quake_pct", "flood_pct", "drought_pct", "plague_pct"]


class ShiftWorldNatureInput(ToolInput):
    world_id: int
    share: Share
    change: int = Field(ge=-100, le=100)
    reason: Reason


async def shift_world_nature(call: SonCall, args: ShiftWorldNatureInput) -> str:
    table = call.rules.world_views
    world = await world_in_reach(call, args.world_id, SonResult.NATURE_REFUSED)
    if args.share not in WORLD_VIEW_SHARES:
        fail(SonResult.NATURE_REFUSED, why=f"a world's nature is moved by {', '.join(WORLD_VIEW_SHARES)}")
    if abs(args.change) > table.son_step or args.change == 0:
        fail(SonResult.NATURE_REFUSED, why=f"you can move it by at most {table.son_step} at once")
    row = await seed_view(call.session, call.rules, world, call.epoch)
    if args.share in row.locked:
        fail(SonResult.NATURE_REFUSED, why=f"the {args.share.replace('_', ' ')} of {world.name} is held fast")
    require_essence(call, table.son_cost)
    value = clamp_int(getattr(row, args.share) + args.change, 0, SHARE_MAX)
    await edit_view(call.tick, world.id, {args.share: value}, [args.share])
    call.spend_essence(table.son_cost)
    call.target(world.id)
    await call.record(
        "tools.son.shift_world_nature",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: world.id},
        facts={"reason": args.reason},
        kind=ChronicleKind.CLIMATE,
    )
    return result(SonResult.NATURE_SHIFTED, world=world.name, share=args.share.replace("_", " "), value=value)


def specs() -> list[ToolSpec[SonCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [ToolSpec(SonToolId.SHIFT_WORLD_NATURE, AgentKind.SON, ShiftWorldNatureInput, meta, shift_world_nature)]
