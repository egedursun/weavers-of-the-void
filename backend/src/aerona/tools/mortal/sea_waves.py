from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.forecasting import ObservationMethodRow
from aerona.db.tables.sea_waves import WaveWarningRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.environment import CleansingMethod, ScarKind
from aerona.domain.enums.forecasting import ObservationMethod
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.region import RegionMemoryKind
from aerona.engine.body.customs import people_of
from aerona.engine.environment.region_control import add_memory
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.sea_waves.sea import WATCHING, coasts_of, sea_of
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.rules.registry import Rules
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


class CleanseLandInput(ToolInput):
    region_id: int
    method: CleansingMethod


def cleansing_depth(rules: Rules, method: CleansingMethod) -> int:
    return {
        CleansingMethod.WORKS: rules.scars.cleanse_works_depth,
        CleansingMethod.RITE: rules.scars.cleanse_rite_depth,
        CleansingMethod.POWER: rules.scars.cleanse_power_depth,
    }[method]


async def cleanse_land(call: MortalCall, args: CleanseLandInput) -> str:
    atlas = await RegionAtlas.load(call.session)
    if atlas.top_region(call.me.id) != args.region_id:
        fail(MortalResult.CLEANSE_REFUSED, why="you cleanse only the land you stand on")
    ground = await call.session.get(RegionEnvironmentRow, args.region_id)
    poison = ground.scars.get(ScarKind.POISONED.value, 0) if ground is not None else 0
    if ground is None or poison <= 0:
        fail(MortalResult.CLEANSE_REFUSED, why="no poison lies in that land")
    if held(args.region_id) or f"scar.{ScarKind.POISONED.value}" in ground.locked:
        fail(MortalResult.CLEANSE_REFUSED, why="a god holds that land unchanged")
    if args.method is CleansingMethod.POWER and ground.magic_density < call.rules.scars.cleanse_power_magic:
        fail(MortalResult.CLEANSE_REFUSED, why="too little power flows in that land")
    lifted = min(poison, cleansing_depth(call.rules, args.method))
    left = poison - lifted
    ground.scars = {key: depth for key, depth in ground.scars.items() if key != ScarKind.POISONED.value} | ({ScarKind.POISONED.value: left} if left else {})
    region = await call.session.get(EntityRow, args.region_id)
    call.target(args.region_id)
    await call.record(
        "scar.cleansed",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: args.region_id},
        facts={"method": args.method, "lifted": lifted, "left": left},
        place=args.region_id,
    )
    return result(MortalResult.LAND_CLEANSED, method=spoken(args.method), lifted=lifted, left=left, place=region.name if region is not None else "the land")


class CommemorateInput(ToolInput):
    region_id: int
    memory: RegionMemoryKind
    title: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


async def commemorate(call: MortalCall, args: CommemorateInput) -> str:
    atlas = await RegionAtlas.load(call.session)
    if atlas.top_region(call.me.id) != args.region_id:
        fail(MortalResult.COMMEMORATE_REFUSED, why="you mark only the land you stand on")
    if held(args.region_id):
        fail(MortalResult.COMMEMORATE_REFUSED, why="a god holds that land unchanged")
    magnitude = call.rules.land_memory.commemorate_magnitude
    await add_memory(call.session, args.region_id, args.memory, magnitude, args.title, epoch=call.tick.epoch, held=False, subject_id=call.me.id)
    region = await call.session.get(EntityRow, args.region_id)
    call.target(args.region_id)
    await call.record(
        "memory.written",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: args.region_id},
        facts={"memory": args.memory, "magnitude": magnitude},
        place=args.region_id,
    )
    return result(MortalResult.COMMEMORATED, place=region.name if region is not None else "the land", title=args.title, memory=spoken(args.memory))


def specs() -> list[ToolSpec[MortalCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.WARN_COAST, AgentKind.MORTAL, WarnCoastInput, meta, warn_coast),
        ToolSpec(MortalToolId.CLEANSE_LAND, AgentKind.MORTAL, CleanseLandInput, meta, cleanse_land),
        ToolSpec(MortalToolId.COMMEMORATE, AgentKind.MORTAL, CommemorateInput, meta, commemorate),
    ]
