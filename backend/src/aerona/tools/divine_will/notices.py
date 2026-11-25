from typing import Any

from pydantic import Field

from aerona.core.grammar import spoken
from aerona.domain.enums.divine_will import CycleNotice, DivineWillMode
from aerona.prompts.tools.divine_will_ids import DivineWillToolId
from aerona.tools.divine_will.framework import Toolset, WillCall, WillResult, WillTool
from aerona.tools.framework.inputs import ToolInput

SUGGEST_MODE_NOTICE = CycleNotice.SUGGEST_MODE.value


class SuggestModeInput(ToolInput):
    mode: DivineWillMode
    reason: str = Field(min_length=1, max_length=600)


async def suggest_mode(call: WillCall, query: SuggestModeInput) -> WillResult:
    if query.mode is call.mode:
        return WillResult(text=f"The exchange is already in {spoken(query.mode)} mode; carry on in it.", is_error=True)
    text = f"The player sees the suggestion to switch to {spoken(query.mode)} mode and decides. Say why in the answer and end the turn without acting."
    return WillResult(text=text, payload={"notice": SUGGEST_MODE_NOTICE, "mode": query.mode.value, "from_mode": call.mode.value, "reason": query.reason})


def tools() -> list[WillTool[Any]]:
    return [WillTool(DivineWillToolId.SUGGEST_MODE, frozenset({Toolset.NOTICES}), SuggestModeInput, suggest_mode)]
