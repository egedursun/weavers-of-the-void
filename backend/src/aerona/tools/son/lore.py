from typing import Any

from aerona.core.errors import AeronaError
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityType
from aerona.engine.gods.queries import worshippers_of
from aerona.engine.lore import rites
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import result
from aerona.tools.framework import lore_tools
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.lore_inputs import CastRiteInput, CommissionInput, DesignRiteInput, FoundSchoolInput, LoreToolResult
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail


async def faithful(call: SonCall, entity_id: int | None) -> int | None:
    worshippers = {entity.id for entity in await worshippers_of(call.session, call.son.id)}
    if entity_id is not None:
        return entity_id if entity_id in worshippers else None
    return min(worshippers) if worshippers else None


async def commission_artwork(call: SonCall, args: CommissionInput) -> str:
    patron = await living_entity(call.session, args.patron_id or await faithful(call, None))
    if patron is None:
        fail(LoreToolResult.NO_PATRON)
    call.target(patron.id)
    return await lore_tools.commission(call.tick, patron, args.model_copy(update={"patron_id": patron.id}))


async def design_rite(call: SonCall, args: DesignRiteInput) -> str:
    holder = await living_entity(call.session, args.holder_id or await faithful(call, None))
    if holder is None:
        fail(LoreToolResult.NO_VESSEL)
    call.target(holder.id)
    return await lore_tools.design(call.tick, holder, args)


async def cast_rite(call: SonCall, args: CastRiteInput) -> str:
    vessel = await living_entity(call.session, await faithful(call, args.vessel_id))
    if vessel is None:
        fail(LoreToolResult.NO_VESSEL)
    rite, row = await lore_tools.rite_of(call.tick, args.rite_id)
    target = await living_entity(call.session, args.target_id) if args.target_id is not None else None
    try:
        casting = await rites.cast_by_son(call.tick, call.son, rite, row, vessel=vessel, target=target)
    except AeronaError as error:
        fail(LoreToolResult.REFUSED, name=rite.name, reason=str(error))
    call.target(rite.id)
    return result(LoreToolResult.CAST, name=rite.name, effect=casting.effect)


async def found_school(call: SonCall, args: FoundSchoolInput) -> str:
    founder = await living_entity(call.session, args.founder_id)
    if founder is None or founder.entity_type is not EntityType.MORTAL:
        fail(LoreToolResult.NO_FOUNDER)
    call.target(founder.id)
    return await lore_tools.found(call.tick, founder, args)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    standard = son_standard_action
    return [
        ToolSpec(SonToolId.COMMISSION_ARTWORK, son, CommissionInput, ToolMeta(ActionKind.CREATE_ENTITY, standard), commission_artwork),
        ToolSpec(SonToolId.DESIGN_RITE, son, DesignRiteInput, ToolMeta(ActionKind.CREATE_ENTITY, standard), design_rite),
        ToolSpec(SonToolId.CAST_RITE, son, CastRiteInput, ToolMeta(ActionKind.MIRACLE, standard), cast_rite),
        ToolSpec(SonToolId.FOUND_SCHOOL, son, FoundSchoolInput, ToolMeta(ActionKind.INFLUENCE, standard), found_school),
    ]
