from typing import Annotated, Any

from pydantic import Field

from aerona.catalog.dangers import DANGERS
from aerona.catalog.gates import Gate
from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.errors import AeronaError
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.happening import RiverShiftCause
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.region import DangerHarm, DangerOrigin, DangerSource, RegionMemoryKind
from aerona.engine.environment import region_control
from aerona.engine.environment.dangers import ease_danger, reaches
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, gate, son_standard_action
from aerona.tools.framework.validation import fail
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
    targets: list[DangerHarm] = Field(default_factory=list)
    reason: Reason


class MarkLandInput(ToolInput):
    region_id: int
    memory: RegionMemoryKind
    magnitude: int = Field(ge=1, le=100)
    title: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
    reason: Reason


class QuellDangerInput(ToolInput):
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
    await call.record(
        "tools.son.sanctify_region",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: region.id},
        facts={"reason": args.reason},
        place=region.id,
        kind=ChronicleKind.MIRACLE,
        world_id=region.world_id,
    )
    return result(SonResult.REGION_SANCTIFIED, name=region.name, sacredness=ground.sacredness)


async def curse_region(call: SonCall, args: CurseRegionInput) -> str:
    cost = call.rules.terrain.curse_essence
    require_essence(call, cost)
    region = await _region(call, args.region_id)
    strength = min(args.strength, call.rules.terrain.curse_strength_max)
    reachable = set(reaches(call.rules, args.danger))
    if any(target not in reachable for target in args.targets):
        fail(SonResult.DANGER_CANNOT_REACH, danger=DANGERS[args.danger].label, reachable=", ".join(sorted(harm.value for harm in reachable)))
    call.target(region.id)
    await region_control.set_danger(
        call.session,
        call.rules,
        region.id,
        args.danger,
        strength,
        epoch=call.tick.epoch,
        held=False,
        origin=DangerOrigin.DIVINE,
        son_id=call.son.id,
        targets=args.targets,
    )
    call.spend_essence(cost)
    label = DANGERS[args.danger].label
    await call.record(
        "tools.son.curse_region",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: region.id},
        facts={"danger": label.lower(), "reason": args.reason},
        place=region.id,
        kind=ChronicleKind.WORLD,
        world_id=region.world_id,
    )
    return result(SonResult.REGION_CURSED, danger=label, name=region.name, strength=strength)


async def mark_land(call: SonCall, args: MarkLandInput) -> str:
    cost = call.rules.son_tools.mark_land_essence
    require_essence(call, cost)
    region = await _region(call, args.region_id)
    if held(region.id):
        fail(SonResult.LAND_UNCHANGED, name=region.name)
    row = await region_control.add_memory(
        call.session, region.id, args.memory, args.magnitude, args.title, epoch=call.tick.epoch, held=False, subject_id=call.son.id
    )
    call.target(region.id)
    call.spend_essence(cost)
    await call.record(
        "memory.written",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: region.id},
        facts={"memory": args.memory, "magnitude": row.magnitude},
        place=region.id,
        world_id=region.world_id,
    )
    return result(SonResult.LAND_MARKED, name=region.name, title=args.title, memory=spoken(args.memory))


async def quell_danger(call: SonCall, args: QuellDangerInput) -> str:
    cost = call.rules.terrain.quell_essence
    require_essence(call, cost)
    region = await _region(call, args.region_id)
    label = DANGERS[args.danger].label
    if held(region.id):
        fail(SonResult.DANGER_ABSENT, danger=label.lower(), name=region.name)
    eased = await ease_danger(call.session, call.rules, region.id, args.danger, args.strength)
    if eased <= 0:
        fail(SonResult.DANGER_ABSENT, danger=label.lower(), name=region.name)
    call.target(region.id)
    call.spend_essence(cost)
    await call.record(
        "tools.son.quell_danger",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: region.id},
        facts={"danger": args.danger, "eased": eased, "reason": args.reason},
        place=region.id,
        world_id=region.world_id,
    )
    return result(SonResult.DANGER_QUELLED, eased=eased, danger=label.lower(), name=region.name)


async def redirect_river(call: SonCall, args: RedirectRiverInput) -> str:
    cost = call.rules.terrain.redirect_essence
    require_essence(call, cost)
    source = await _region(call, args.from_region_id)
    target = await _region(call, args.to_region_id)
    try:
        moved = await region_control.redirect_river(call.session, call.rules, source.id, target.id, epoch=call.tick.epoch, cause=RiverShiftCause.DIVINE)
    except AeronaError as error:
        fail(SonResult.RIVER_NOT_TURNED, reason=error.message)
    call.target(target.id)
    call.spend_essence(cost)
    river = spoken(moved.river)
    await call.record(
        "tools.son.redirect_river",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: source.id, IncidentRole.TARGET: target.id},
        facts={"river": str(river), "reason": args.reason},
        kind=ChronicleKind.WORLD,
        world_id=source.world_id,
    )
    return result(SonResult.RIVER_REDIRECTED, river=river, source=source.name, target=target.name)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    rare = gate(Gate.RARE_TOOLS)
    return [
        ToolSpec(
            SonToolId.MARK_LAND,
            son,
            MarkLandInput,
            ToolMeta(ActionKind.MIRACLE, son_standard_action, essence_cost=lambda rules: rules.son_tools.mark_land_essence),
            mark_land,
        ),
        ToolSpec(
            SonToolId.SANCTIFY_REGION,
            son,
            SanctifyInput,
            ToolMeta(ActionKind.MIRACLE, son_standard_action, essence_cost=lambda rules: rules.terrain.sanctify_essence, rarity_gate=rare),
            sanctify_region,
        ),
        ToolSpec(
            SonToolId.QUELL_DANGER,
            son,
            QuellDangerInput,
            ToolMeta(ActionKind.MIRACLE, son_standard_action, essence_cost=lambda rules: rules.terrain.quell_essence),
            quell_danger,
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
