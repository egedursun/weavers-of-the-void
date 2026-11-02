from pydantic import Field

from aerona.prompts.contexts.base import ContextItem
from aerona.prompts.contexts.cosmos import StarLine


class ToolTextContext(ContextItem):
    power_ceiling: int | None = None
    example_cost: int | None = None
    stars: list[StarLine] = Field(default_factory=list)
