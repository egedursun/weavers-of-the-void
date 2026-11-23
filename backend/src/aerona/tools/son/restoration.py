from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.restoration import RestorationBasis
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.restoration.rise import RestorationTally, open_for, raise_movement
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class StirMemoryInput(ToolInput):
    fallen_polity_id: int
    reason: Reason


async def stir_memory(call: SonCall, args: StirMemoryInput) -> str:
    fallen = await call.session.get(EntityRow, args.fallen_polity_id)
    if fallen is None or fallen.entity_type is not EntityType.POLITY or fallen.status is EntityStatus.CANON:
        fail(SonResult.RESTORATION_REFUSED, why="only a realm that has fallen is remembered")
    await ensure_in_reach(call, fallen)
    if held(fallen.id):
        fail(SonResult.RESTORATION_REFUSED, why="that realm is held as it is")
    row = await open_for(call.tick, fallen.id) or await raise_movement(
        call.tick, fallen, claimant=None, bases=[RestorationBasis.MEMORY], territories=[], tally=RestorationTally()
    )
    if "memory" in (row.locked or []):
        fail(SonResult.RESTORATION_REFUSED, why="its memory is held as it is")
    row.memory = clamp_int(row.memory + call.tick.rules.restoration.stir_memory, 0, PERCENT)
    call.target(fallen.id)
    await call.record("polity.memory_stirred", roles={IncidentRole.SUBJECT: fallen.id}, facts={"memory": row.memory})
    return result(SonResult.MEMORY_STIRRED, realm=fallen.name, memory=row.memory)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.STIR_MEMORY, AgentKind.SON, StirMemoryInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), stir_memory)]
