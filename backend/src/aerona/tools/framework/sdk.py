from typing import Any

from claude_agent_sdk import SdkMcpTool

from aerona.prompts.tools.text import RenderedToolText
from aerona.tools.framework.runtime import ToolRuntime
from aerona.tools.framework.schema import input_schema
from aerona.tools.framework.spec import ToolSpec


def sdk_tool(runtime: ToolRuntime[Any], spec: ToolSpec[Any, Any], text: RenderedToolText) -> SdkMcpTool[Any]:
    name = spec.name

    async def handler(arguments: dict[str, Any]) -> dict[str, Any]:
        outcome = await runtime.call(name, dict(arguments or {}))
        return {"content": [{"type": "text", "text": outcome.text}], "is_error": outcome.is_error}

    return SdkMcpTool(name=name, description=text.description, input_schema=input_schema(spec.input_model, text.fields), handler=handler)
