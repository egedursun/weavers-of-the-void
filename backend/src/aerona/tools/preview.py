from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.civilization import unlocked
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.agent import ToolBlock
from aerona.domain.enums.rarity import Rarity
from aerona.prompts import tool_text
from aerona.prompts.tools.ids import MortalToolId, SonToolId
from aerona.rules.registry import Rules
from aerona.tools.framework.ports import ToolPorts
from aerona.tools.framework.spec import ToolSpec
from aerona.tools.mortal import registry as mortal_registry
from aerona.tools.son import registry as son_registry
from aerona.tools.son.availability import condition_holds, world_state


@dataclass(frozen=True)
class ToolPreview:
    name: str
    description: str
    fields: dict[str, str]
    action_cost: int
    essence_cost: int
    read_only: bool
    long_job: bool
    minimum_rarity: Rarity | None


@dataclass(frozen=True)
class BlockedTool:
    name: str
    reason: ToolBlock
    minimum_rarity: Rarity | None


@dataclass(frozen=True)
class ToolAvailability:
    available: list[ToolPreview]
    blocked: list[BlockedTool]


def _preview(spec: ToolSpec[Any, Any], rules: Rules, text_description: str, text_fields: dict[str, str]) -> ToolPreview:
    return ToolPreview(
        name=spec.name,
        description=text_description,
        fields=text_fields,
        action_cost=spec.meta.actions(rules),
        essence_cost=spec.meta.essence(rules),
        read_only=spec.meta.read_only,
        long_job=spec.meta.long_job is not None,
        minimum_rarity=spec.meta.minimum_rarity(rules),
    )


async def son_tool_availability(session: AsyncSession, rules: Rules, son: SonRow, ports: ToolPorts) -> ToolAvailability:
    state = await world_state(session, son)
    available: list[ToolPreview] = []
    blocked: list[BlockedTool] = []
    for spec in son_registry.son_specs():
        minimum = spec.meta.minimum_rarity(rules)
        if minimum is not None and not son.rarity.at_least(minimum):
            blocked.append(BlockedTool(spec.name, ToolBlock.RARITY, minimum))
        elif not son_registry.ports_allow(spec, ports):
            blocked.append(BlockedTool(spec.name, ToolBlock.UNWIRED, minimum))
        elif not condition_holds(SonToolId(spec.name), rules, state):
            blocked.append(BlockedTool(spec.name, ToolBlock.WORLD_STATE, minimum))
        else:
            text = tool_text(SonToolId(spec.name), rules, await son_registry.son_text_context(session, rules, son, spec))
            available.append(_preview(spec, rules, text.description, dict(text.fields)))
    return ToolAvailability(available, blocked)


async def mortal_tool_availability(session: AsyncSession, rules: Rules, mortal: EntityRow, ports: ToolPorts) -> ToolAvailability:
    state = await mortal_registry.mortal_state(session, rules, mortal)
    available: list[ToolPreview] = []
    blocked: list[BlockedTool] = []
    for spec in mortal_registry.mortal_specs():
        tool_id = MortalToolId(spec.name)
        allowed = mortal_registry.ACTOR_TYPES.get(tool_id)
        capability = mortal_registry.TIER_GATES.get(tool_id)
        condition = mortal_registry.CONDITIONS.get(tool_id)
        if allowed is not None and mortal.entity_type not in allowed:
            blocked.append(BlockedTool(spec.name, ToolBlock.ACTOR_TYPE, None))
        elif capability is not None and not unlocked(rules, state.tier, capability):
            blocked.append(BlockedTool(spec.name, ToolBlock.CIVILIZATION_TIER, None))
        elif "views" in spec.tags and ports.views is None:
            blocked.append(BlockedTool(spec.name, ToolBlock.UNWIRED, None))
        elif condition is not None and not condition(rules, state):
            blocked.append(BlockedTool(spec.name, ToolBlock.WORLD_STATE, None))
        else:
            text = tool_text(tool_id, rules, mortal_registry.mortal_text_context(spec))
            available.append(_preview(spec, rules, text.description, dict(text.fields)))
    return ToolAvailability(available, blocked)
