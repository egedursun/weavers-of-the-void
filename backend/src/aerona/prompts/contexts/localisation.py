from pydantic import Field

from aerona.prompts.contexts.base import ContextItem, LoreContext


class EngineLine(ContextItem):
    id: int
    text: str


class LocaliseContext(LoreContext):
    world_name: str
    lines: list[EngineLine] = Field(default_factory=list)
