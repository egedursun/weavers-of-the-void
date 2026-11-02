import os
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, SdkMcpTool, create_sdk_mcp_server

from aerona.constants.llm import FORCED_ENVIRONMENT, HAIKU_MODEL_ID, OAUTH_TOKEN_KEY, STRIPPED_ENVIRONMENT_KEYS, TOOL_NAME_PREFIX, TOOL_SERVER_NAME
from aerona.constants.paths import AGENT_WORKDIR
from aerona.settings import get_settings


def sandbox_environment() -> dict[str, str]:
    environment = {key: value for key, value in os.environ.items() if key not in STRIPPED_ENVIRONMENT_KEYS}
    environment.update(FORCED_ENVIRONMENT)
    token = get_settings().claude_code_oauth_token.get_secret_value()
    if token:
        environment[OAUTH_TOKEN_KEY] = token
    return environment


def build_options(
    system_prompt: str,
    max_turns: int,
    *,
    tools: list[SdkMcpTool[Any]] | None = None,
    output_schema: dict[str, Any] | None = None,
) -> ClaudeAgentOptions:
    AGENT_WORKDIR.mkdir(parents=True, exist_ok=True)
    tool_list = tools or []
    servers: dict[str, Any] = {TOOL_SERVER_NAME: create_sdk_mcp_server(TOOL_SERVER_NAME, tools=tool_list)} if tool_list else {}
    return ClaudeAgentOptions(
        model=HAIKU_MODEL_ID,
        fallback_model=None,
        system_prompt=system_prompt,
        max_turns=max_turns,
        tools=[],
        allowed_tools=[f"{TOOL_NAME_PREFIX}{item.name}" for item in tool_list],
        mcp_servers=servers,
        strict_mcp_config=True,
        setting_sources=[],
        include_partial_messages=True,
        permission_mode="bypassPermissions",
        cwd=str(AGENT_WORKDIR),
        env=sandbox_environment(),
        output_format={"type": "json_schema", "schema": output_schema} if output_schema else None,
    )
