from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolText:
    description: str
    fields: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RenderedToolText:
    description: str
    fields: Mapping[str, str]
