from collections.abc import Sequence
from typing import Any, Protocol

from claude_agent_sdk import SdkMcpTool

from aerona.tools.framework.runtime import DoneAction, ToolCatalogue

__all__ = ["DoneAction", "SpeechOnlyToolkit", "ToolCatalogue", "ToolkitFactory", "TurnToolkit"]


class TurnToolkit(Protocol):
    @property
    def catalogue(self) -> ToolCatalogue: ...

    @property
    def done(self) -> Sequence[DoneAction]: ...

    @property
    def created_entity_ids(self) -> Sequence[int]: ...

    @property
    def read_only_tools(self) -> frozenset[str]: ...

    def tools(self) -> list[SdkMcpTool[Any]]: ...

    async def settle_long_jobs(self) -> None: ...


class ToolkitFactory(Protocol):
    async def son_toolkit(self, son_id: int, epoch: int, action_points: int) -> TurnToolkit: ...

    async def mortal_toolkit(self, entity_id: int, epoch: int, action_points: int) -> TurnToolkit: ...


class SpeechOnlyToolkit:
    def __init__(self) -> None:
        self._done: list[DoneAction] = []

    @property
    def catalogue(self) -> ToolCatalogue:
        return ToolCatalogue()

    @property
    def done(self) -> Sequence[DoneAction]:
        return self._done

    @property
    def created_entity_ids(self) -> Sequence[int]:
        return ()

    @property
    def read_only_tools(self) -> frozenset[str]:
        return frozenset()

    def tools(self) -> list[SdkMcpTool[Any]]:
        return []

    async def settle_long_jobs(self) -> None:
        return None
