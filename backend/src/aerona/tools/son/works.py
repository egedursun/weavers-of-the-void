from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.db.tables.industry import RegionPollutionRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.industry import Pollutant
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.industry.pollution import shift
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail, require_canon, require_type
from aerona.tools.son.support import require_essence


class TendInput(ToolInput):
    region_id: int
    cleanse: bool = True
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


async def tend_land(call: SonCall, args: TendInput) -> str:
    region = require_type(await require_canon(call.session, args.region_id), {EntityType.REGION}, SonResult.NOT_A_REGION, name=str(args.region_id))
    cost = call.rules.costs.influence
    require_essence(call, cost)
    row = await call.session.get(RegionPollutionRow, region.id)
    if row is None:
        row = RegionPollutionRow(region_node_id=region.id, air=0, water=0, soil=0, polluters={}, epoch=call.epoch, locked=[])
        call.session.add(row)
    amount = call.rules.son_tools.touch_amount * (-1 if args.cleanse else 1)
    for pollutant in Pollutant:
        shift(row, pollutant, amount)
    if all(pollutant.value in row.locked for pollutant in Pollutant):
        fail(SonResult.LAND_HELD, name=region.name)
    call.spend_essence(cost)
    call.target(region.id)
    await call.record(
        "tools.son.tend_land",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: region.id},
        facts={"verb": str("cleansed" if args.cleanse else "fouled"), "reason": str(args.reason)},
        place=region.id,
        kind=ChronicleKind.WORLD,
    )
    return result(SonResult.LAND_TENDED, name=region.name, air=row.air, water=row.water, soil=row.soil)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [
        ToolSpec(
            SonToolId.TEND_LAND,
            AgentKind.SON,
            TendInput,
            ToolMeta(ActionKind.INFLUENCE, son_standard_action, essence_cost=lambda rules: rules.costs.influence),
            tend_land,
        ),
    ]
