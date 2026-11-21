from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.sea_waves import WaveOrigin
from aerona.engine.phases.disasters import strike_disaster
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.sea_waves.waves import raise_wave
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class RaiseSeaInput(ToolInput):
    sea_id: int
    strength: int = Field(ge=1, le=PERCENT)
    reason: Reason


async def raise_sea(call: SonCall, args: RaiseSeaInput) -> str:
    sea = await call.session.get(EntityRow, args.sea_id)
    atlas = await RegionAtlas.load(call.session)
    if sea is None or not atlas.is_water(sea.id):
        fail(SonResult.SEA_REFUSED, why="that is no sea")
    await ensure_in_reach(call, sea)
    if held(sea.id):
        fail(SonResult.SEA_REFUSED, why="a stronger hand holds that sea still")
    wave = await raise_wave(call.tick, sea.id, WaveOrigin.DIVINE, args.strength / PERCENT, strike=strike_disaster, cause=call.son.id, sure=True, atlas=atlas)
    if wave is None:
        fail(SonResult.SEA_REFUSED, why="that sea has no coast to strike")
    call.target(sea.id)
    return result(SonResult.SEA_RAISED, sea=sea.name, strength=wave.strength)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.RAISE_SEA, AgentKind.SON, RaiseSeaInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), raise_sea)]
