from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.catalog.strata import STRATA
from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.geology import RegionStratumRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.geology import DeepPassageOrigin, DeepPassageState, UndergroundStratum
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.environment.cells import make_passage, passage_between, shape_cell, tell, underworld_of
from aerona.engine.environment.deep import DeepTally, reach_stratum
from aerona.engine.primitives.deep import Cell, passage_kind, shape_fault
from aerona.engine.primitives.distance import RegionAtlas
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
    to_region_id: int | None = None
    to_stratum: UndergroundStratum | None = None
    reason: Reason


async def stratum_of(call: SonCall, args: DeepInput, *, create: bool = False) -> tuple[EntityRow, RegionEnvironmentRow, RegionStratumRow]:
    region = await call.session.get(EntityRow, args.region_id)
    ground = await call.session.get(RegionEnvironmentRow, args.region_id)
    if region is None or region.entity_type is not EntityType.REGION or ground is None:
        fail(SonResult.NOT_A_REGION, name=region.name if region is not None else str(args.region_id))
    await ensure_in_reach(call, region)
    row = await call.session.scalar(
        select(RegionStratumRow).where(RegionStratumRow.region_entity_id == region.id, RegionStratumRow.stratum == args.stratum).limit(1)
    )
    if held(region.id):
        fail(SonResult.DEEP_ABSENT, stratum=STRATA[args.stratum].label.lower(), name=region.name)
    require_essence(call, call.rules.underground.open_essence)
    if row is None:
        if not create:
            fail(SonResult.DEEP_ABSENT, stratum=STRATA[args.stratum].label.lower(), name=region.name)
        row = RegionStratumRow(region_entity_id=region.id, stratum=args.stratum, volume=0, pressure=0, by_node_id=call.son.id, locked=[])
        shape_cell(
            call.rules, row, ground, call.tick.rng(f"son.cell.{region.id}.{args.stratum.value}").below(100), await underworld_of(call.tick, region.world_id)
        )
        call.session.add(row)
        await call.session.flush()
        await call.record(
            "deep.cell_formed",
            roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: region.id},
            facts={"stratum": args.stratum},
            place=region.id,
            world_id=region.world_id,
        )
    return region, ground, row


async def region_name(call: SonCall, region_id: int | None) -> str:
    region = await call.session.get(EntityRow, region_id) if region_id is not None else None
    return region.name if region is not None else "another land"


async def passage_ends(call: SonCall, args: DeepInput, region: EntityRow) -> tuple[Cell, Cell] | None:
    if args.to_region_id is None:
        return None
    first: Cell = (region.id, args.stratum)
    second: Cell = (args.to_region_id, args.to_stratum)
    atlas = await RegionAtlas.load(call.session)
    fault = shape_fault(first, second, second[0] in atlas.neighbours(first[0]))
    if fault is not None or held(second[0]):
        fail(SonResult.DEEP_ABSENT, stratum=STRATA[args.stratum].label.lower(), name=region.name)
    return first, second


async def open_the_deep(call: SonCall, args: DeepInput) -> str:
    region, ground, row = await stratum_of(call, args, create=True)
    ends = await passage_ends(call, args, region)
    if ends is not None:
        passage = await passage_between(call.tick, *ends) or await make_passage(
            call.tick, region.world_id or 0, *ends, origin=DeepPassageOrigin.DIVINE, by_node_id=call.son.id
        )
        passage.state = DeepPassageState.OPEN
        await tell(call.tick, "deep.passage_formed", passage, call.son.id)
        call.spend_essence(call.rules.underground.open_essence)
        call.target(region.id)
        return result(SonResult.PASSAGE_OPENED, kind=spoken(passage_kind(*ends)), first=region.name, second=await region_name(call, args.to_region_id))
    await reach_stratum(call.tick, ground, row, DeepTally())
    call.spend_essence(call.rules.underground.open_essence)
    call.target(region.id)
    return result(SonResult.DEEP_OPENED, stratum=STRATA[args.stratum].label.lower(), name=region.name)


async def close_the_deep(call: SonCall, args: DeepInput) -> str:
    region, _, row = await stratum_of(call, args)
    ends = await passage_ends(call, args, region)
    if ends is not None:
        passage = await passage_between(call.tick, *ends)
        if passage is None or "state" in passage.locked:
            fail(SonResult.DEEP_ABSENT, stratum=STRATA[args.stratum].label.lower(), name=region.name)
        passage.state, passage.progress = DeepPassageState.COLLAPSED, 0
        await tell(call.tick, "deep.passage_collapsed", passage, call.son.id)
        call.spend_essence(call.rules.underground.open_essence)
        call.target(region.id)
        return result(SonResult.PASSAGE_CLOSED, kind=spoken(passage_kind(*ends)), first=region.name, second=await region_name(call, args.to_region_id))
    dwellers = await call.session.scalar(select(EntityRow.id).where(EntityRow.location_id == region.id, EntityRow.stratum == args.stratum).limit(1))
    if dwellers is None and "stratum" not in row.locked:
        await call.session.delete(row)
        call.spend_essence(call.rules.underground.open_essence)
        call.target(region.id)
        await call.record(
            "deep.cell_lost",
            roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: region.id},
            facts={"stratum": args.stratum},
            place=region.id,
            world_id=region.world_id,
        )
        return result(SonResult.DEEP_REMOVED, stratum=STRATA[args.stratum].label.lower(), name=region.name)
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
