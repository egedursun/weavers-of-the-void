from typing import Any

from pydantic import Field

from aerona.constants.units import PERCENT
from aerona.db.tables.water import CoastRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.economy.purse import take_coin
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import top_region
from aerona.engine.recording.terms import explaining_alone, term
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail


class DredgeInput(ToolInput):
    region_id: int | None = None
    budget: int = Field(ge=1, le=1000)


async def dredge(call: MortalCall, args: DredgeInput) -> str:
    home = await top_region(call.session, call.me)
    region_id = args.region_id if args.region_id is not None else (home.id if home is not None else None)
    if region_id is None or home is None or region_id != home.id:
        fail(MortalResult.DREDGE_REFUSED, why="you can dredge only the harbour of the land you live in")
    coast = await call.session.get(CoastRow, region_id)
    if coast is None:
        fail(MortalResult.DREDGE_REFUSED, why="your land has no coast to dredge")
    if held(region_id) or "harbour_silting" in coast.locked:
        fail(MortalResult.DREDGE_REFUSED, why="a god holds this harbour as it is")
    if coast.harbour_silting <= 0:
        fail(MortalResult.DREDGE_REFUSED, why="the harbour is clear")
    unit = max(1, call.rules.water_and_ice.dredge_cost)
    cleared = min(coast.harbour_silting, args.budget // unit)
    if cleared <= 0:
        fail(MortalResult.DREDGE_REFUSED, why=f"one point of silting costs {unit} coin")
    cost = cleared * unit
    if not await take_coin(call.session, call.rules, call.me, cost):
        fail(MortalResult.DREDGE_REFUSED, why=f"it costs {cost} coin and you have less")
    with explaining_alone():
        term("water_and_ice.dredge", -cleared, source_node_id=call.me.id)
        coast.harbour_silting = clamp_int(coast.harbour_silting - cleared, 0, PERCENT)
    call.target(region_id)
    await call.record(
        "land.dredged",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: region_id},
        facts={"cost": cost, "silting": coast.harbour_silting},
        place=region_id,
    )
    return result(MortalResult.DREDGED, cost=cost, silting=coast.harbour_silting)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [ToolSpec(MortalToolId.DREDGE, AgentKind.MORTAL, DredgeInput, meta, dredge)]
