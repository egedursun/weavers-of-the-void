from typing import Annotated, Any

from pydantic import Field

from aerona.catalog.dangers import DANGERS
from aerona.catalog.gates import Gate
from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.errors import AeronaError
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.region import DangerOrigin, DangerSource
from aerona.engine.environment import region_control
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, gate, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son import lines
from aerona.tools.son.support import ensure_in_reach, require_essence

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class SanctifyInput(ToolInput):
    region_id: int
    sacredness: int | None = Field(default=None, ge=0, le=100)
    reason: Reason


class CurseRegionInput(ToolInput):
    region_id: int
    danger: DangerSource
    strength: int = Field(ge=1, le=100)
    reason: Reason


class RedirectRiverInput(ToolInput):
    from_region_id: int
    to_region_id: int
    reason: Reason


async def _region(call: SonCall, region_id: int) -> EntityRow:
    region = await call.session.get(EntityRow, region_id)
    if region is None or region.entity_type is not EntityType.REGION:
        fail(SonResult.NOT_A_REGION, name=region.name if region is not None else str(region_id))
    await ensure_in_reach(call, region)
    return region


async def sanctify_region(call: SonCall, args: SanctifyInput) -> str:
    cost = call.rules.terrain.sanctify_essence
    require_essence(call, cost)
    region = await _region(call, args.region_id)
    call.target(region.id)
    ground = await region_control.sanctify(call.session, call.rules, region.id, args.sacredness, held=True)
    call.spend_essence(cost)
    await call.chronicle(
        ChronicleKind.MIRACLE,
        lines.SANCTIFY_REGION,
        entity_ids=[region.id],
        world_id=region.world_id,
        son=call.son.name,
        region=region.name,
        reason=args.reason,
    )
    return result(SonResult.REGION_SANCTIFIED, name=region.name, sacredness=ground.sacredness)


async def curse_region(call: SonCall, args: CurseRegionInput) -> str:
    cost = call.rules.terrain.curse_essence
    require_essence(call, cost)
    region = await _region(call, args.region_id)
    strength = min(args.strength, call.rules.terrain.curse_strength_max)
    call.target(region.id)
    await region_control.set_danger(
        call.session, call.rules, region.id, args.danger, strength, epoch=call.tick.epoch, held=False, origin=DangerOrigin.DIVINE, son_id=call.son.id
    )
    call.spend_essence(cost)
    label = DANGERS[args.danger].label
    await call.chronicle(
        ChronicleKind.WORLD,
        lines.CURSE_REGION,
        entity_ids=[region.id],
        world_id=region.world_id,
        son=call.son.name,
        danger=label.lower(),
        region=region.name,
        reason=args.reason,
    )
    return result(SonResult.REGION_CURSED, danger=label, name=region.name, strength=strength)


async def redirect_river(call: SonCall, args: RedirectRiverInput) -> str:
    cost = call.rules.terrain.redirect_essence
    require_essence(call, cost)
    source = await _region(call, args.from_region_id)
    target = await _region(call, args.to_region_id)
    try:
        moved = await region_control.redirect_river(call.session, call.rules, source.id, target.id)
    except AeronaError as error:
        fail(SonResult.RIVER_NOT_TURNED, reason=error.message)
    call.target(target.id)
    call.spend_essence(cost)
    river = moved.river.value.replace("_", " ")
    await call.chronicle(
        ChronicleKind.WORLD,
        lines.REDIRECT_RIVER,
        entity_ids=[source.id, target.id],
        world_id=source.world_id,
        son=call.son.name,
        river=river,
        source=source.name,
        target=target.name,
        reason=args.reason,
    )
    return result(SonResult.RIVER_REDIRECTED, river=river, source=source.name, target=target.name)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    rare = gate(Gate.RARE_TOOLS)
    return [
        ToolSpec(
            SonToolId.SANCTIFY_REGION,
            son,
            SanctifyInput,
            ToolMeta(ActionKind.MIRACLE, son_standard_action, essence_cost=lambda rules: rules.terrain.sanctify_essence, rarity_gate=rare),
            sanctify_region,
        ),
        ToolSpec(
            SonToolId.CURSE_REGION,
            son,
            CurseRegionInput,
            ToolMeta(ActionKind.CURSE, son_standard_action, essence_cost=lambda rules: rules.terrain.curse_essence, rarity_gate=rare),
            curse_region,
        ),
        ToolSpec(
            SonToolId.REDIRECT_RIVER,
            son,
            RedirectRiverInput,
            ToolMeta(ActionKind.PLANET_ACT, son_standard_action, essence_cost=lambda rules: rules.terrain.redirect_essence, rarity_gate=rare),
            redirect_river,
        ),
    ]
