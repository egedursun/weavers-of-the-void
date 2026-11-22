from typing import Annotated, Any

from pydantic import Field

from aerona.catalog.life.eras import LIVE
from aerona.catalog.techniques import TECHNIQUES
from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.constants.units import PERCENT
from aerona.db.tables.eras import TechProgrammeRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class SabotageProgrammeInput(ToolInput):
    programme_id: int
    reason: Reason


async def sabotage_programme(call: SonCall, args: SabotageProgrammeInput) -> str:
    row = await call.session.get(TechProgrammeRow, args.programme_id)
    if row is None or row.stage not in LIVE:
        fail(SonResult.PROGRAMME_UNTOUCHED, why="no such programme is under way")
    realm = await living_entity(call.session, row.polity_entity_id)
    if realm is None or realm.world_id != call.son.current_world_id:
        fail(SonResult.PROGRAMME_UNTOUCHED, why="you can hinder only a programme of the world you stand on")
    if held(realm.id) or "progress" in row.locked:
        fail(SonResult.PROGRAMME_UNTOUCHED, why="a stronger hand holds it")
    row.progress = clamp_int(row.progress - call.tick.rules.programmes.sabotage_loss * 2, 0, PERCENT)
    row.sabotaged += 1
    call.target(realm.id)
    label = TECHNIQUES[row.technique].label.lower()
    await call.record(
        "tools.son.sabotage_programme",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: realm.id},
        facts={"technique": label, "reason": args.reason},
        kind=ChronicleKind.CIVILIZATION,
    )
    return result(SonResult.PROGRAMME_HINDERED, realm=realm.name, technique=label, progress=row.progress)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [ToolSpec(SonToolId.SABOTAGE_PROGRAMME, son, SabotageProgrammeInput, meta, sabotage_programme)]
