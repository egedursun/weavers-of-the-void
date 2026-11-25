from typing import Any

from pydantic import Field

from aerona.db.repositories.divine_will import remembered_cycle_ids
from aerona.db.tables.divine_will import DivineWillHandleRow
from aerona.prompts.tools.divine_will_ids import DivineWillToolId
from aerona.tools.divine_will import act, artifacts, attachments, foresight, mechanics, notices, plans, read, retrieval
from aerona.tools.divine_will.framework import Toolset, WillCall, WillResult, WillTool, invoke
from aerona.tools.divine_will.paging import failed
from aerona.tools.framework.inputs import ToolInput

PAGE_FIELD = "page"


class ReadMoreInput(ToolInput):
    handle: str = Field(min_length=1, max_length=64)


async def read_more(call: WillCall, query: ReadMoreInput) -> WillResult:
    async with call.database.read() as session:
        row = await session.get(DivineWillHandleRow, query.handle)
        if row is None:
            return failed(f"No result is kept under handle {query.handle}.")
        if row.cycle_id not in await remembered_cycle_ids(session, call.session_id, call.rules.divine_will.remembered_cycles):
            return failed("That handle belongs to an exchange beyond memory. Run the tool again to read its result.")
        tool, arguments = row.tool, dict(row.query)
    found = tool_by_name(tool)
    if found is None:
        return failed(f"The tool {tool} behind this handle is no longer offered.")
    if PAGE_FIELD not in found.input_model.model_fields:
        return failed(f"{tool} returns its whole result at once; there is no further page.")
    page = arguments.get(PAGE_FIELD)
    arguments[PAGE_FIELD] = (page if isinstance(page, int) else 1) + 1
    return await invoke(call, found, arguments)


def every_tool() -> list[WillTool[Any]]:
    return [
        *read.tools(),
        WillTool(DivineWillToolId.READ_MORE, frozenset(Toolset), ReadMoreInput, read_more),
        *act.tools(),
        *mechanics.tools(),
        *notices.tools(),
        *retrieval.tools(),
        *attachments.tools(),
        *plans.tools(),
        *foresight.tools(),
        *artifacts.tools(),
    ]


def tool_by_name(name: str) -> WillTool[Any] | None:
    return next((tool for tool in every_tool() if tool.name == name), None)
