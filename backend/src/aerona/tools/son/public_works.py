from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.works import PublicWorksRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.works import WorksStatus
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class BlessWorksInput(ToolInput):
    works_id: int
    reason: Reason


async def bless_works(call: SonCall, args: BlessWorksInput) -> str:
    works = await call.session.get(PublicWorksRow, args.works_id)
    if works is None or works.status is WorksStatus.FAILED:
        fail(SonResult.WORKS_REFUSED, why="there are no such works standing")
    builder = await living_entity(call.session, works.polity_entity_id)
    if builder is None:
        fail(SonResult.WORKS_REFUSED, why="their builder is gone")
    await ensure_in_reach(call, builder)
    if held(works.polity_entity_id) or held(works.place_node_id) or "quality" in (works.locked or []):
        fail(SonResult.WORKS_REFUSED, why="they are held")
    works.quality = clamp_int(works.quality + call.rules.public_works.blessing_quality, 0, PERCENT)
    if works.status is WorksStatus.FINISHED and "condition" not in (works.locked or []):
        works.condition = PERCENT
    call.target(works.polity_entity_id)
    await call.record(
        "works.blessed",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: works.place_node_id},
        facts={"kind": works.kind, "reason": args.reason},
    )
    return result(SonResult.WORKS_BLESSED, kind=spoken(works.kind), quality=works.quality)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.BLESS_WORKS, AgentKind.SON, BlessWorksInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), bless_works)]
