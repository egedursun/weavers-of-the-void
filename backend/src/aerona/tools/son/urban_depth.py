from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import DistrictRow
from aerona.db.tables.urban import ConvoyRow, TurfRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.urban import ConvoyStatus
from aerona.engine.economy.convoys import OPEN
from aerona.engine.primitives.numbers import clamp_int
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son import lines
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
DIVINE_GUARDS = 10
SCOURED = 30


class ShieldConvoyInput(ToolInput):
    convoy_id: int
    reason: Reason


class ScourStreetsInput(ToolInput):
    district_id: int
    reason: Reason


async def shield_convoy(call: SonCall, args: ShieldConvoyInput) -> str:
    convoy = await call.session.get(ConvoyRow, args.convoy_id)
    route = await call.session.get(EntityRow, convoy.route_entity_id) if convoy is not None else None
    if convoy is None or route is None or convoy.status not in OPEN:
        fail(SonResult.CONVOY_REFUSED, why="no such convoy is on the road")
    await ensure_in_reach(call, route)
    if "guards" not in convoy.locked:
        convoy.guards += DIVINE_GUARDS
    if convoy.status is ConvoyStatus.DELAYED and "status" not in convoy.locked:
        convoy.status = ConvoyStatus.TRAVELLING
    call.target(route.id)
    await call.chronicle(ChronicleKind.WORLD, lines.SHIELD_CONVOY, entity_ids=[route.id], son=call.son.name, route=route.name, reason=args.reason)
    return result(SonResult.CONVOY_SHIELDED, name=route.name)


async def scour_streets(call: SonCall, args: ScourStreetsInput) -> str:
    district = await call.session.get(DistrictRow, args.district_id)
    town = await call.session.get(EntityRow, district.settlement_entity_id) if district is not None else None
    if district is None or town is None:
        fail(SonResult.STREETS_REFUSED, why="there is no such district")
    await ensure_in_reach(call, town)
    scoured = 0
    for turf in await call.session.scalars(select(TurfRow).where(TurfRow.district_id == district.id)):
        if "strength" not in turf.locked:
            turf.strength = clamp_int(turf.strength - SCOURED, 0, PERCENT)
            scoured += 1
    call.target(town.id)
    await call.chronicle(ChronicleKind.WORLD, lines.SCOUR_STREETS, entity_ids=[town.id], son=call.son.name, town=town.name, reason=args.reason)
    return result(SonResult.STREETS_SCOURED, name=town.name, count=scoured)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [
        ToolSpec(SonToolId.SHIELD_CONVOY, son, ShieldConvoyInput, meta, shield_convoy),
        ToolSpec(SonToolId.SCOUR_STREETS, son, ScourStreetsInput, meta, scour_streets),
    ]
