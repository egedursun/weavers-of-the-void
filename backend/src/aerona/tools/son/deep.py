from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.catalog.strata import STRATA
from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.geology import RegionStratumRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.geology import UndergroundStratum
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.environment.deep import DeepTally, reach_stratum
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach, require_essence

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class DeepInput(ToolInput):
    region_id: int
    stratum: UndergroundStratum
    reason: Reason


async def stratum_of(call: SonCall, args: DeepInput) -> tuple[EntityRow, RegionEnvironmentRow, RegionStratumRow]:
    region = await call.session.get(EntityRow, args.region_id)
    ground = await call.session.get(RegionEnvironmentRow, args.region_id)
    if region is None or region.entity_type is not EntityType.REGION or ground is None:
        fail(SonResult.NOT_A_REGION, name=region.name if region is not None else str(args.region_id))
    await ensure_in_reach(call, region)
    row = await call.session.scalar(
        select(RegionStratumRow).where(RegionStratumRow.region_entity_id == region.id, RegionStratumRow.stratum == args.stratum).limit(1)
    )
    if row is None or held(region.id):
        fail(SonResult.DEEP_ABSENT, stratum=STRATA[args.stratum].label.lower(), name=region.name)
    require_essence(call, call.rules.underground.open_essence)
    return region, ground, row


async def open_the_deep(call: SonCall, args: DeepInput) -> str:
    region, ground, row = await stratum_of(call, args)
    await reach_stratum(call.tick, ground, row, DeepTally())
    call.spend_essence(call.rules.underground.open_essence)
    call.target(region.id)
    return result(SonResult.DEEP_OPENED, stratum=STRATA[args.stratum].label.lower(), name=region.name)


async def close_the_deep(call: SonCall, args: DeepInput) -> str:
    region, _, row = await stratum_of(call, args)
    row.reached_epoch = None
    row.breached_epoch = None
    call.spend_essence(call.rules.underground.open_essence)
    call.target(region.id)
    await call.record(
        "deep.stratum_closed",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: region.id},
        facts={"stratum": args.stratum},
        place=region.id,
        world_id=region.world_id,
    )
    return result(SonResult.DEEP_CLOSED, stratum=STRATA[args.stratum].label.lower(), name=region.name)


def specs() -> list[ToolSpec[SonCall, Any]]:
    meta = ToolMeta(ActionKind.RESHAPE_LAND, son_standard_action, essence_cost=lambda rules: rules.underground.open_essence)
    return [
        ToolSpec(SonToolId.OPEN_THE_DEEP, AgentKind.SON, DeepInput, meta, open_the_deep),
        ToolSpec(SonToolId.CLOSE_THE_DEEP, AgentKind.SON, DeepInput, meta, close_the_deep),
    ]
