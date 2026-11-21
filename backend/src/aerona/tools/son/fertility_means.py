from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.fertility_means import FertilityMeansRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.fertility_means import FertilityMeans, MeansSource
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.customs import people_of
from aerona.engine.fertility_means.factor import conceives
from aerona.engine.fertility_means.tend import MeansTally, adopt
from aerona.engine.primitives.numbers import clamp_int
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
CHANGE_MAX = 50


class MoveFertilityInput(ToolInput):
    community_id: int
    means: FertilityMeans
    reliability_change: int = Field(ge=-CHANGE_MAX, le=CHANGE_MAX)
    reason: Reason


async def move_fertility(call: SonCall, args: MoveFertilityInput) -> str:
    community = await call.session.get(EntityRow, args.community_id)
    people = await people_of(call.session, community) if community is not None else None
    if community is None or people is None:
        fail(SonResult.FERTILITY_REFUSED, why="that is no people or community of a people")
    await ensure_in_reach(call, community)
    if held(people.id) or not await conceives(call.session, people.id):
        fail(SonResult.FERTILITY_REFUSED, why="that people is held, or does not conceive")
    row = await call.session.get(FertilityMeansRow, (people.id, args.means))
    if row is None:
        row = await adopt(call.tick, people.id, args.means, MeansSource.POWER, reliability=max(0, args.reliability_change), tally=MeansTally())
    elif "reliability" in row.locked:
        fail(SonResult.FERTILITY_REFUSED, why="a stronger hand holds that means as it is")
    else:
        row.reliability = clamp_int(row.reliability + args.reliability_change, 0, PERCENT)
    call.target(people.id)
    await call.record("birth.fertility_moved", roles={IncidentRole.SUBJECT: people.id}, facts={"means": args.means, "reliability": row.reliability})
    return result(SonResult.FERTILITY_MOVED, means=spoken(args.means), name=people.name, reliability=row.reliability)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.MOVE_FERTILITY, AgentKind.SON, MoveFertilityInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), move_fertility)]
