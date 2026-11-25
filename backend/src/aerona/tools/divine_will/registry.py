from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from aerona.domain.enums.divine_will import DivineWillMode
from aerona.prompts.tools import (
    divine_will_act,
    divine_will_attachments,
    divine_will_library,
    divine_will_mechanics,
    divine_will_notices,
    divine_will_read,
    divine_will_retrieval,
)
from aerona.prompts.tools.divine_will_ids import DivineWillToolId
from aerona.tools.divine_will.catalogue import every_tool as catalogued
from aerona.tools.divine_will.framework import MODE_TOOLSETS, Toolset, WillTool

TEXTS: tuple[tuple[Mapping[DivineWillToolId, str], Mapping[DivineWillToolId, Mapping[str, str]]], ...] = (
    (divine_will_read.DESCRIPTIONS, divine_will_read.FIELDS),
    (divine_will_retrieval.DESCRIPTIONS, divine_will_retrieval.FIELDS),
    (divine_will_act.DESCRIPTIONS, divine_will_act.FIELDS),
    (divine_will_mechanics.DESCRIPTIONS, divine_will_mechanics.FIELDS),
    (divine_will_notices.DESCRIPTIONS, divine_will_notices.FIELDS),
    (divine_will_attachments.DESCRIPTIONS, divine_will_attachments.FIELDS),
    (divine_will_library.DESCRIPTIONS, divine_will_library.FIELDS),
)


@dataclass(frozen=True)
class WillToolText:
    description: str
    fields: Mapping[str, str]


def every_tool() -> list[WillTool[Any]]:
    found: dict[DivineWillToolId, WillTool[Any]] = {}
    for tool in catalogued():
        if tool.tool_id in found:
            raise ValueError(f"The Divine Will tool {tool.name} is registered twice.")
        found[tool.tool_id] = tool
    return list(found.values())


def mode_tools(mode: DivineWillMode) -> list[WillTool[Any]]:
    offered = MODE_TOOLSETS[mode]
    return [tool for tool in every_tool() if tool.toolsets & offered]


def mode_toolsets(mode: DivineWillMode) -> list[Toolset]:
    return sorted(MODE_TOOLSETS[mode])


def tool_text(tool_id: DivineWillToolId) -> WillToolText:
    for descriptions, fields in TEXTS:
        if tool_id in descriptions:
            return WillToolText(descriptions[tool_id], dict(fields.get(tool_id, {})))
    raise LookupError(tool_id)
