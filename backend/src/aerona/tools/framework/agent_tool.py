from typing import Any

from aerona.llm.tools import AgentTool, ToolReply
from aerona.prompts.schemas.order import order_for, unordered
from aerona.prompts.tools.text import RenderedToolText
from aerona.tools.framework.runtime import ToolRuntime
from aerona.tools.framework.schema import input_schema
from aerona.tools.framework.spec import ToolSpec


def agent_tool(runtime: ToolRuntime[Any], spec: ToolSpec[Any, Any], text: RenderedToolText) -> AgentTool:
    name = spec.name

    async def handler(arguments: dict[str, Any]) -> ToolReply:
        outcome = await runtime.call(name, dict(arguments or {}))
        return ToolReply(outcome.text, outcome.is_error)

    settings = runtime.settings
    order = order_for(f"{settings.world_seed}/{settings.epoch}/{settings.actor_node_id}/{name}")
    return AgentTool(name=name, description=text.description, input_schema=unordered(input_schema(spec.input_model, text.fields), order), handler=handler)
