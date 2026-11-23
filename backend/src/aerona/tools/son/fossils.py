from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.grammar import spoken
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.ecology.fossil_control import first_hidden
from aerona.engine.ecology.fossils import FossilTally, finder_in, reveal
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach, require_essence

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class LayBareFossilsInput(ToolInput):
    region_id: int
    reason: Reason


async def lay_bare_fossils(call: SonCall, args: LayBareFossilsInput) -> str:
    region = await living_entity(call.session, args.region_id)
    if region is None or region.entity_type is not EntityType.REGION:
        fail(SonResult.FOSSILS_REFUSED, why="there is no such land")
    await ensure_in_reach(call, region)
    if held(region.id):
        fail(SonResult.FOSSILS_REFUSED, why="that land is held")
    bed = await first_hidden(call.tick, region.id)
    if bed is None or "found_epoch" in bed.locked:
        fail(SonResult.FOSSILS_REFUSED, why=f"no hidden remains lie in {region.name}")
    cost = call.rules.fossils.son_cost
    require_essence(call, cost)
    await reveal(call.tick, bed, await finder_in(call.tick, region.id), FossilTally())
    call.spend_essence(cost)
    call.target(region.id)
    await call.record(
        "tools.son.lay_bare_fossils",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: region.id},
        facts={"reason": args.reason},
        place=region.id,
        kind=ChronicleKind.DIVINE_SIGN,
    )
    return result(SonResult.FOSSILS_LAID_BARE, region=region.name, source=spoken(bed.source), reading=spoken(bed.reading))


def specs() -> list[ToolSpec[SonCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [ToolSpec(SonToolId.LAY_BARE_FOSSILS, AgentKind.SON, LayBareFossilsInput, meta, lay_bare_fossils)]
