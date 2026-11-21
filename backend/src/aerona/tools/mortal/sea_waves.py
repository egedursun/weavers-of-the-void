from typing import Any

from sqlalchemy import select

from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.forecasting import ObservationMethodRow
from aerona.db.tables.sea_waves import WaveWarningRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.forecasting import ObservationMethod
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.customs import people_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.sea_waves.sea import WATCHING, coasts_of, sea_of
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail


class WarnCoastInput(ToolInput):
    region_id: int
    method: ObservationMethod


async def watches(call: MortalCall, people_id: int, method: ObservationMethod) -> bool:
    known = (ObservationMethodRow.people_entity_id == people_id, ObservationMethodRow.method == method, ObservationMethodRow.domain.in_(WATCHING))
    return await call.session.scalar(select(ObservationMethodRow.id).where(*known).limit(1)) is not None


async def warn_coast(call: MortalCall, args: WarnCoastInput) -> str:
    atlas = await RegionAtlas.load(call.session)
    if atlas.top_region(call.me.id) != args.region_id:
        fail(MortalResult.WARNING_REFUSED, why="you warn only the coast you stand on")
    if not any(args.region_id in coasts_of(atlas, sea_of(atlas, water)) for water in atlas.neighbours(args.region_id) if atlas.is_water(water)):
        fail(MortalResult.WARNING_REFUSED, why="that land lies on no sea")
    people = await people_of(call.session, call.me)
    if people is None or not await watches(call, people.id, args.method):
        fail(MortalResult.WARNING_REFUSED, why=f"your people do not watch the waters by {spoken(args.method)}")
    if held(args.region_id):
        fail(MortalResult.WARNING_REFUSED, why="a god holds that coast unchanged")
    until = call.tick.epoch + call.rules.sea_waves.warning_epochs
    call.session.add(
        WaveWarningRow(region_entity_id=args.region_id, method=args.method, by_node_id=call.me.id, epoch=call.tick.epoch, until_epoch=until, locked=[])
    )
    region = await call.session.get(EntityRow, args.region_id)
    call.target(args.region_id)
    await call.record("land.coast_warning", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: args.region_id}, facts={"method": args.method})
    return result(MortalResult.COAST_WARNED, place=region.name if region is not None else "the coast", until=until)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [ToolSpec(MortalToolId.WARN_COAST, AgentKind.MORTAL, WarnCoastInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), warn_coast)]
