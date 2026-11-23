from typing import Annotated, Any

from pydantic import Field

from aerona.catalog.domain_powers import LAND_DOMAINS
from aerona.catalog.gates import Gate
from aerona.catalog.life.tools import ACT_WORDS
from aerona.catalog.stats import PERCENT
from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import ScarKind
from aerona.domain.enums.happening import LandAct
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.environment.book import add_scar
from aerona.engine.environment.shaping import LandOutcome, reshape_ground
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, gate
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import require_essence

FIERY = frozenset({Domain.FIRE, Domain.ASH, Domain.EARTH, Domain.STONE})


class ReshapeLandInput(ToolInput):
    region_id: int
    act: LandAct
    target_region_id: int | None = None
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


async def reshape_land(call: SonCall, args: ReshapeLandInput) -> str:
    tools = call.rules.son_tools
    domains = {call.son.domain_primary, call.son.domain_secondary}
    if not domains & LAND_DOMAINS[args.act]:
        fail(SonResult.LAND_NOT_YOURS, act=spoken(args.act))
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
    await call.record(
        "tools.son.reshape_land",
        roles={
            IncidentRole.ACTOR: call.son.id,
            IncidentRole.PLACE: region.id,
            IncidentRole.SUBJECT: [*[region.id, *([args.target_region_id] if args.target_region_id is not None else [])]],
        },
        facts={"act": str(ACT_WORDS[args.act]), "reason": str(args.reason)},
        place=region.id,
        kind=ChronicleKind.COSMIC,
        world_id=region.world_id,
    )
    return result(SonResult.LAND_RESHAPED, name=region.name, act=ACT_WORDS[args.act])


class WoundLandInput(ToolInput):
    region_id: int
    scar: ScarKind
    depth: Annotated[int, Field(ge=1, le=PERCENT)]
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class HealLandInput(ToolInput):
    region_id: int
    scar: ScarKind
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


async def scarred_region(call: SonCall, region_id: int) -> tuple[EntityRow, RegionEnvironmentRow]:
    region = await call.session.get(EntityRow, region_id)
    ground = await call.session.get(RegionEnvironmentRow, region_id)
    if region is None or region.entity_type is not EntityType.REGION or ground is None:
        fail(SonResult.LAND_NOT_REGION, id=region_id)
    if call.world_id != region.world_id and not await call.reachable_world(region.world_id):
        fail(SonResult.SEASONS_OUT_OF_REACH, name=region.name)
    return region, ground


async def wound_land(call: SonCall, args: WoundLandInput) -> str:
    region, ground = await scarred_region(call, args.region_id)
    if held(region.id) or f"scar.{args.scar.value}" in ground.locked:
        fail(SonResult.LAND_UNCHANGED, name=region.name)
    require_essence(call, call.rules.son_tools.wound_land_essence)
    depth = add_scar(ground, args.scar, args.depth)
    call.spend_essence(call.rules.son_tools.wound_land_essence)
    call.target(region.id)
    await call.record(
        "scar.made",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: region.id},
        facts={"scar": args.scar, "depth": depth},
        place=region.id,
        world_id=region.world_id,
    )
    return result(SonResult.LAND_WOUNDED, scar=spoken(args.scar), name=region.name, depth=depth)


async def heal_land(call: SonCall, args: HealLandInput) -> str:
    region, ground = await scarred_region(call, args.region_id)
    if ground.scars.get(args.scar.value, 0) <= 0:
        fail(SonResult.LAND_NOT_SCARRED, name=region.name, scar=spoken(args.scar))
    if held(region.id) or f"scar.{args.scar.value}" in ground.locked:
        fail(SonResult.LAND_UNCHANGED, name=region.name)
    require_essence(call, call.rules.son_tools.heal_land_essence)
    ground.scars = {key: depth for key, depth in ground.scars.items() if key != args.scar.value}
    call.spend_essence(call.rules.son_tools.heal_land_essence)
    call.target(region.id)
    await call.record(
        "scar.healed",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: region.id},
        facts={"scar": args.scar},
        place=region.id,
        world_id=region.world_id,
    )
    return result(SonResult.LAND_HEALED, scar=spoken(args.scar), name=region.name)


def specs() -> list[ToolSpec[SonCall, Any]]:
    scarring = ToolMeta(ActionKind.RESHAPE_LAND, lambda rules: rules.son_tools.reshape_land_ap, essence_cost=lambda rules: rules.son_tools.wound_land_essence)
    healing = ToolMeta(ActionKind.RESHAPE_LAND, lambda rules: rules.son_tools.reshape_land_ap, essence_cost=lambda rules: rules.son_tools.heal_land_essence)
    return [
        ToolSpec(SonToolId.WOUND_LAND, AgentKind.SON, WoundLandInput, scarring, wound_land),
        ToolSpec(SonToolId.HEAL_LAND, AgentKind.SON, HealLandInput, healing, heal_land),
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
        ),
    ]
