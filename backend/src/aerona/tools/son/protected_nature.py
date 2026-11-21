from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.constants.units import PERCENT
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.protected_nature import ProtectedUse, ProtectionBasis
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.engine.protected_nature.areas import protect_area
from aerona.engine.protected_nature.book import NatureTally
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
HALLOWING = 30


class HallowWildInput(ToolInput):
    region_id: int
    reason: Reason


async def hallow_wild(call: SonCall, args: HallowWildInput) -> str:
    region = await living_entity(call.session, args.region_id)
    if region is None or region.entity_type is not EntityType.REGION:
        fail(SonResult.HALLOWING_REFUSED, why="there is no such land")
    await ensure_in_reach(call, region)
    if held(region.id):
        fail(SonResult.HALLOWING_REFUSED, why="a stronger hand holds that land as it is")
    row = await protect_area(
        call.tick, region, ProtectionBasis.DIVINE_DECREE, [ProtectedUse.HUNTING, ProtectedUse.LOGGING], NatureTally(), protector=call.son.id
    )
    if "strength" not in (row.locked or []):
        row.strength = clamp_int(row.strength + HALLOWING, 0, PERCENT)
    call.target(region.id)
    await call.record("nature.hallowed", roles={IncidentRole.SUBJECT: region.id}, facts={"strength": row.strength})
    return result(SonResult.WILD_HALLOWED, region=region.name, strength=row.strength)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.HALLOW_WILD, AgentKind.SON, HallowWildInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), hallow_wild)]
