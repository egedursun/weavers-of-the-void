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
from aerona.engine.leagues.book import core_of, members_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
BIND_MAX = 30


class BindLeagueInput(ToolInput):
    league_id: int
    strength_change: int = Field(ge=-BIND_MAX, le=BIND_MAX)
    reason: Reason


async def bind_league(call: SonCall, args: BindLeagueInput) -> str:
    league = await call.session.get(EntityRow, args.league_id)
    if league is None or league.entity_type is not EntityType.LEAGUE or league.status is not EntityStatus.CANON:
        fail(SonResult.LEAGUE_REFUSED, why="there is no such league")
    members = await members_of(call.session, league.id)
    cores = [core for core in [await core_of(call.session, member.polity_entity_id) for member in members] if core is not None]
    seat = await call.session.get(EntityRow, cores[0]) if cores else None
    await ensure_in_reach(call, seat if seat is not None else league)
    if held(league.id) or not args.strength_change:
        fail(SonResult.LEAGUE_REFUSED, why="that league is held, or nothing would change")
    strength = clamp_int(stat_or(league, "strength", 0) + args.strength_change, 0, PERCENT)
    set_stats(league, strength=strength)
    call.target(league.id)
    await call.record("league.bound", roles={IncidentRole.SUBJECT: league.id}, facts={"change": args.strength_change, "strength": strength})
    return result(SonResult.LEAGUE_BOUND, league=league.name, strength=strength)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.BIND_LEAGUE, AgentKind.SON, BindLeagueInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), bind_league)]
