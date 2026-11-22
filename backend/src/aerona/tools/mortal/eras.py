from typing import Any

from aerona.catalog.life.eras import LIVE, SPECIALISMS
from aerona.catalog.techniques import TECHNIQUES
from aerona.constants.units import PERCENT
from aerona.db.tables.eras import TechProgrammeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.cycles.book import realm_of
from aerona.engine.mind.book import skills_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail


class JoinProgrammeInput(ToolInput):
    programme_id: int


async def join_programme(call: MortalCall, args: JoinProgrammeInput) -> str:
    me = call.me
    row = await call.session.get(TechProgrammeRow, args.programme_id)
    if row is None or row.stage not in LIVE:
        fail(MortalResult.PROGRAMME_REFUSED, why="no such programme is under way")
    realm = await realm_of(call.session, me.location_id) if me.location_id is not None else None
    if realm != row.polity_entity_id:
        fail(MortalResult.PROGRAMME_REFUSED, why="it is not a programme of your realm")
    skills = await skills_of(call.session, me.id)
    best = max((skills[skill].level for skill in SPECIALISMS if skill in skills), default=0)
    if best < call.tick.rules.programmes.specialist_skill:
        fail(MortalResult.PROGRAMME_REFUSED, why="you lack the science, engineering or computing it needs")
    if "progress" not in row.locked:
        row.progress = clamp_int(row.progress + call.tick.rules.programmes.specialist_progress, 0, PERCENT)
    call.target(row.polity_entity_id)
    label = TECHNIQUES[row.technique].label.lower()
    await call.record(
        "tools.mortal.join_programme", roles={IncidentRole.ACTOR: me.id, IncidentRole.AUTHORITY: row.polity_entity_id}, facts={"technique": row.technique}
    )
    return result(MortalResult.PROGRAMME_JOINED, technique=label, progress=row.progress)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [ToolSpec(MortalToolId.JOIN_PROGRAMME, mortal, JoinProgrammeInput, meta, join_programme)]
