from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.climes import OCTANT_MAX, RegionWindRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.climes import DIRECTIONS, CirculationBand
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.climes import control
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
STRONG = 160
FAILED = 30


class StirMonsoonInput(ToolInput):
    world_id: int
    strong: bool
    reason: Reason


class TurnWindInput(ToolInput):
    region_id: int
    wind_from: Annotated[int, Field(ge=0, le=OCTANT_MAX)]
    reason: Reason


async def stir_monsoon(call: SonCall, args: StirMonsoonInput) -> str:
    world = await call.session.get(WorldRow, args.world_id)
    if world is None:
        fail(SonResult.MONSOON_REFUSED, why="there is no such world")
    if args.world_id != call.son.current_world_id:
        fail(SonResult.MONSOON_REFUSED, why="you can stir the monsoon only of the world you stand on")
    if held(args.world_id):
        fail(SonResult.MONSOON_REFUSED, why="a stronger hand holds it")
    strength = STRONG if args.strong else FAILED
    values = {"strength": strength, "failed": strength < call.tick.rules.monsoons.fail_below}
    await control.set_record(call.tick, "monsoon_season", {"world_id": world.id, "epoch": call.tick.epoch}, values)
    told = "a strong monsoon" if args.strong else "the failing of the monsoon"
    await call.record(
        "tools.son.stir_monsoon",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: world.id},
        facts={"told": str(told), "reason": args.reason},
        kind=ChronicleKind.CLIMATE,
    )
    return result(SonResult.MONSOON_STIRRED, world=world.name, strong=args.strong)


async def turn_wind(call: SonCall, args: TurnWindInput) -> str:
    region = await living_entity(call.session, args.region_id)
    if region is None or region.entity_type is not EntityType.REGION:
        fail(SonResult.WIND_REFUSED, why="there is no such land")
    await ensure_in_reach(call, region)
    if held(region.id):
        fail(SonResult.WIND_REFUSED, why="a stronger hand holds it")
    row = await call.session.get(RegionWindRow, region.id)
    band = row.band if row is not None else CirculationBand.TRADE
    await control.set_record(call.tick, "region_wind", {"region_entity_id": region.id}, {"band": band, "wind_from": args.wind_from})
    call.target(region.id)
    direction = DIRECTIONS[args.wind_from]
    await call.record(
        "tools.son.turn_wind",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: region.id},
        facts={"direction": str(direction), "reason": args.reason},
        place=region.id,
        kind=ChronicleKind.CLIMATE,
    )
    return result(SonResult.WIND_TURNED, region=region.name, direction=direction)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [
        ToolSpec(SonToolId.STIR_MONSOON, son, StirMonsoonInput, meta, stir_monsoon),
        ToolSpec(SonToolId.TURN_WIND, son, TurnWindInput, meta, turn_wind),
    ]
