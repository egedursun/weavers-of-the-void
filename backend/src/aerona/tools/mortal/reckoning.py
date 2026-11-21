from typing import Any

from pydantic import Field
from sqlalchemy import select

from aerona.core.grammar import spoken
from aerona.db.tables.interconnect import IncidentParticipantRow
from aerona.db.tables.reckoning import ReckoningMeasureRow, ReckoningRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.reckoning import ReckoningMeasure
from aerona.engine.leagues.book import living_polity
from aerona.engine.primitives.queries import living_entity
from aerona.engine.reckoning.book import ReckoningTally
from aerona.engine.reckoning.measures import open_case, try_case
from aerona.engine.reckoning.opening import FULL, open_reckoning
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.monetary import controls

MEASURES_MAX = 9
ACTS_MAX = 12


class OpenReckoningInput(ToolInput):
    polity_id: int
    fallen_regime_id: int | None = None
    measures: list[ReckoningMeasure] = Field(min_length=1, max_length=MEASURES_MAX)


class TryServantInput(ToolInput):
    reckoning_id: int
    accused_id: int
    incident_ids: list[int] = Field(default_factory=list, max_length=ACTS_MAX)


async def open_reckoning_tool(call: MortalCall, args: OpenReckoningInput) -> str:
    realm = await living_polity(call.session, args.polity_id)
    if realm is None or not await controls(call, realm.id):
        fail(MortalResult.RECKONING_REFUSED, why="only the ruler of a realm opens a reckoning in it")
    if held(realm.id):
        fail(MortalResult.RECKONING_REFUSED, why="a god holds that realm as it is")
    measures = [(measure, FULL) for measure in dict.fromkeys(args.measures)]
    row = await open_reckoning(call.tick, realm, args.fallen_regime_id, measures, by=call.me.id, fallen_epoch=call.tick.epoch, tally=ReckoningTally())
    call.target(realm.id)
    return result(MortalResult.RECKONING_OPENED, realm=realm.name, measures=", ".join(spoken(measure) for measure, _strength in measures), reckoning=row.id)


async def try_servant_tool(call: MortalCall, args: TryServantInput) -> str:
    row = await call.session.get(ReckoningRow, args.reckoning_id)
    if row is None or row.closed_epoch is not None:
        fail(MortalResult.RECKONING_REFUSED, why="there is no such reckoning still open")
    if not await controls(call, row.polity_entity_id):
        fail(MortalResult.RECKONING_REFUSED, why="only the ruler of the realm brings a servant to trial")
    accused = await living_entity(call.session, args.accused_id)
    if accused is None or held(accused.id):
        fail(MortalResult.RECKONING_REFUSED, why="the accused must be living and no god may hold them")
    named = select(IncidentParticipantRow.incident_id).where(
        IncidentParticipantRow.node_id == accused.id, IncidentParticipantRow.incident_id.in_(args.incident_ids)
    )
    acts = sorted(set(await call.session.scalars(named)))
    if len(acts) < len(set(args.incident_ids)):
        fail(MortalResult.RECKONING_REFUSED, why="a trial names only deeds the record ties to the accused")
    case = await open_case(call.tick, row, accused, ReckoningMeasure.TRIBUNAL)
    case.incident_ids = sorted(set(case.incident_ids or []) | set(acts))
    court = ReckoningMeasureRow(reckoning_id=row.id, polity_entity_id=row.polity_entity_id, measure=ReckoningMeasure.TRIBUNAL, strength=FULL, locked=[])
    await try_case(call.tick, row, court, case, accused=accused, tally=ReckoningTally())
    call.target(accused.id)
    return result(MortalResult.SERVANT_TRIED, accused=accused.name, outcome=spoken(case.outcome))


def specs() -> list[ToolSpec[MortalCall, Any]]:
    act = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.OPEN_RECKONING, AgentKind.MORTAL, OpenReckoningInput, act, open_reckoning_tool),
        ToolSpec(MortalToolId.TRY_SERVANT, AgentKind.MORTAL, TryServantInput, act, try_servant_tool),
    ]
