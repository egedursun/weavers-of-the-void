from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.gathering import GatheringKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.gatherings.hold import plan
from aerona.engine.gatherings.occasions import Occasion
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail, require_canon, require_type
from aerona.tools.son.support import ensure_in_reach

HOSTS = frozenset({*COMMUNITY_TYPES, EntityType.CULT, EntityType.PLACE})
SON_KINDS = frozenset(
    {GatheringKind.FESTIVAL, GatheringKind.PROCESSION, GatheringKind.PILGRIMAGE, GatheringKind.FEAST, GatheringKind.GAMES, GatheringKind.PERFORMANCE}
)


class ConveneGatheringInput(ToolInput):
    host_id: int
    kind: GatheringKind
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


async def convene_gathering(call: SonCall, args: ConveneGatheringInput) -> str:
    if args.kind not in SON_KINDS:
        fail(SonResult.GATHERING_REFUSED, why="a son calls only gatherings of the faithful and of the people")
    host = require_type(
        await require_canon(call.session, args.host_id), HOSTS, SonResult.GATHERING_REFUSED, why="only a people, settlement, cult or place hosts it"
    )
    await ensure_in_reach(call, host)
    row = await plan(call.tick, Occasion(args.kind, host.id, host.world_id, host.id))
    if row is None:
        fail(SonResult.GATHERING_REFUSED, why=f"{host.name} is held against change")
    call.target(host.id)
    kind = args.kind.value.replace("_", " ")
    await call.record(
        "tools.son.convene_gathering",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.HOST: host.id},
        facts={"kind": str(kind), "reason": str(args.reason)},
        kind=ChronicleKind.WORLD,
    )
    return result(SonResult.GATHERING_CONVENED, kind=kind, host=host.name, id=row.id)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [
        ToolSpec(SonToolId.CONVENE_GATHERING, AgentKind.SON, ConveneGatheringInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), convene_gathering),
    ]
