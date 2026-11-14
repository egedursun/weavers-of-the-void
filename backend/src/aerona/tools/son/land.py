from typing import Annotated, Any

from pydantic import Field

from aerona.catalog.gates import Gate
from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.happening import LandAct
from aerona.engine.environment.shaping import LandOutcome, reshape_ground
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, gate
from aerona.tools.framework.validation import fail
from aerona.tools.son import lines
from aerona.tools.son.support import require_essence

LAND_DOMAINS: dict[LandAct, frozenset[Domain]] = {
    LandAct.SHIFT_RIVER: frozenset({Domain.SEA, Domain.STORM, Domain.EARTH, Domain.STONE}),
    LandAct.PARCH: frozenset({Domain.SUN, Domain.FIRE, Domain.HUNGER, Domain.SALT, Domain.ASH}),
    LandAct.GREEN: frozenset({Domain.PLANTS, Domain.HARVEST, Domain.LIFE, Domain.SEA}),
    LandAct.SALT_SOIL: frozenset({Domain.SALT, Domain.SEA, Domain.DEATH}),
    LandAct.ENRICH_SOIL: frozenset({Domain.EARTH, Domain.FIRE, Domain.ASH, Domain.HARVEST, Domain.PLANTS, Domain.STONE}),
    LandAct.RAISE_LAND: frozenset({Domain.EARTH, Domain.STONE}),
    LandAct.LOWER_LAND: frozenset({Domain.EARTH, Domain.STONE, Domain.SEA}),
    LandAct.CARVE_VALLEY: frozenset({Domain.EARTH, Domain.STONE, Domain.STORM, Domain.SEA}),
    LandAct.FILL_VALLEY: frozenset({Domain.EARTH, Domain.STONE, Domain.ASH}),
    LandAct.OPEN_SPRING: frozenset({Domain.SEA, Domain.LIFE, Domain.EARTH, Domain.PLANTS}),
    LandAct.CALL_LAVA: frozenset({Domain.FIRE, Domain.EARTH, Domain.ASH, Domain.STONE}),
    LandAct.SINK_COAST: frozenset({Domain.SEA, Domain.STORM, Domain.EARTH}),
}
FIERY = frozenset({Domain.FIRE, Domain.ASH, Domain.EARTH, Domain.STONE})
ACT_WORDS = {
    LandAct.SHIFT_RIVER: "moved its river",
    LandAct.PARCH: "parched it into desert",
    LandAct.GREEN: "brought the grass back",
    LandAct.SALT_SOIL: "made its soil saline",
    LandAct.ENRICH_SOIL: "made its soil rich",
    LandAct.RAISE_LAND: "raised the land",
    LandAct.LOWER_LAND: "lowered the land",
    LandAct.CARVE_VALLEY: "carved a valley",
    LandAct.FILL_VALLEY: "filled its valleys",
    LandAct.OPEN_SPRING: "opened a spring",
    LandAct.CALL_LAVA: "called up lava",
    LandAct.SINK_COAST: "sank its coast",
}


class ReshapeLandInput(ToolInput):
    region_id: int
    act: LandAct
    target_region_id: int | None = None
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


async def reshape_land(call: SonCall, args: ReshapeLandInput) -> str:
    tools = call.rules.son_tools
    domains = {call.son.domain_primary, call.son.domain_secondary}
    if not domains & LAND_DOMAINS[args.act]:
        fail(SonResult.LAND_NOT_YOURS, act=args.act.value.replace("_", " "))
    region = await call.session.get(EntityRow, args.region_id)
    ground = await call.session.get(RegionEnvironmentRow, args.region_id)
    if region is None or region.entity_type is not EntityType.REGION or ground is None:
        fail(SonResult.LAND_NOT_REGION, id=args.region_id)
    if call.world_id != region.world_id and not await call.reachable_world(region.world_id):
        fail(SonResult.SEASONS_OUT_OF_REACH, name=region.name)
    require_essence(call, tools.reshape_land_essence)
    outcome = await reshape_ground(call.tick, region, ground, args.act, god_id=call.son.id, fiery=bool(domains & FIERY), target_region_id=args.target_region_id)
    if outcome is LandOutcome.NO_RIVER:
        fail(SonResult.LAND_NO_RIVER, name=region.name)
    if outcome is LandOutcome.NO_COAST:
        fail(SonResult.LAND_NO_COAST, name=region.name)
    if outcome is LandOutcome.UNCHANGED:
        fail(SonResult.LAND_UNCHANGED, name=region.name)
    call.spend_essence(tools.reshape_land_essence)
    call.target(region.id)
    await call.chronicle(
        ChronicleKind.COSMIC,
        lines.RESHAPE_LAND,
        entity_ids=[region.id, *([args.target_region_id] if args.target_region_id is not None else [])],
        world_id=region.world_id,
        son=call.son.name,
        region=region.name,
        act=ACT_WORDS[args.act],
        reason=args.reason,
    )
    return result(SonResult.LAND_RESHAPED, name=region.name, act=ACT_WORDS[args.act])


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [
        ToolSpec(
            SonToolId.RESHAPE_LAND,
            AgentKind.SON,
            ReshapeLandInput,
            ToolMeta(
                ActionKind.RESHAPE_LAND,
                lambda rules: rules.son_tools.reshape_land_ap,
                essence_cost=lambda rules: rules.son_tools.reshape_land_essence,
                rarity_gate=gate(Gate.RARE_TOOLS),
            ),
            reshape_land,
        )
    ]
