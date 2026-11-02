from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from aerona.db.tables.motifs import MotifOverrideMode
from aerona.domain.enums.agent import AgentKind
from aerona.prompts.ids import PromptArea, PromptId
from aerona.prompts.tools.ids import MortalToolId, SonToolId


class ContextBlockKind(StrEnum):
    WORLD_HEADER = "world-header"
    DIALECT = "dialect"
    WORLD_LINE = "world-line"
    COSMOS = "cosmos"
    PANTHEON = "pantheon"
    THREADS = "threads"
    WORLD_SUMMARY = "world-summary"
    FATE_SUMMARY = "fate-summary"
    GEOGRAPHY = "geography"
    MAP = "map"
    LANGUAGES = "languages"
    ENTITY_LINE = "entity-line"
    ENTITY_DETAIL = "entity-detail"
    BOND_LINES = "bond-lines"
    SON_MEMORY = "son-memory"
    TIRED_IMAGES = "tired-images"
    RECENT_EVENTS = "recent-events"
    POWERS = "powers"
    SKY_CALENDAR = "sky-calendar"
    MORTAL = "mortal"
    CHRONICLER = "chronicler"


class ContextBlockInfo(BaseModel):
    kind: ContextBlockKind
    needs_son: bool
    needs_entity: bool
    audience: str
    rows: list[str]


class ContextBlock(BaseModel):
    kind: ContextBlockKind
    text: str
    characters: int
    token_estimate: int
    world_id: int | None
    son_id: int | None
    entity_id: int | None


class SectionBudget(BaseModel):
    section: str
    characters: int
    limit: int | None


class SonPromptPreview(BaseModel):
    son_id: int
    son_name: str
    epoch: int
    action_points: int
    system_prompt: str
    user_prompt: str
    system_characters: int
    user_characters: int
    total_characters: int
    token_estimate: int
    prompt_limit: int
    over_limit: bool
    tool_names: list[str]
    paid_tools: list[str]
    free_tools: list[str]
    summary_sections: list[SectionBudget]
    summary_characters: int
    summary_limit: int
    memory_characters: int
    memory_limit: int


class PromptVariable(BaseModel):
    name: str
    type: str
    required: bool


class PromptEntry(BaseModel):
    prompt_id: PromptId
    area: PromptArea
    template_path: str
    context: str
    variables: list[PromptVariable]
    output: str | None
    has_constraints: bool


class PromptDetail(PromptEntry):
    template_source: str
    output_schema: dict[str, Any] | None


class ToolEntry(BaseModel):
    tool_id: SonToolId | MortalToolId
    agent: AgentKind
    description: str
    read_only: bool
    action_cost: int
    essence_cost: int
    minimum_rarity: str | None
    long_job: bool
    input_schema: dict[str, Any]


class PromptCatalogue(BaseModel):
    prompts: list[PromptEntry]
    son_tools: list[ToolEntry]
    mortal_tools: list[ToolEntry]


class TiredMotifView(BaseModel):
    key: str
    percent: int
    pinned: bool


class MotifOverrideView(BaseModel):
    id: int
    world_id: int | None
    motif: str
    mode: MotifOverrideMode


class TiredMotifReport(BaseModel):
    world_id: int | None
    motifs: list[TiredMotifView]
    foreign_images: list[str]
    overrides: list[MotifOverrideView]
