from pydantic import Field

from aerona.prompts.contexts.base import ContextItem, PromptContext


class AccountRole(ContextItem):
    role: str
    name: str
    id: int | None = None
    seen: str | None = None


class AccountFactLine(ContextItem):
    key: str
    value: str


class AccountStepLine(ContextItem):
    position: int
    round: int | None = None
    text: str


class EventAccountContext(PromptContext):
    id: int
    name: str | None = None
    epoch: int
    year: int | None = None
    place: str | None = None
    line: str | None = None
    told: str | None = None
    fidelity: int | None = None
    differences: list[str] = Field(default_factory=list)
    roles: list[AccountRole] = Field(default_factory=list)
    facts: list[AccountFactLine] = Field(default_factory=list)
    steps: list[AccountStepLine] = Field(default_factory=list)
    step_offset: int = 0
    more_steps: int = 0
    cause: str | None = None
    effects: list[str] = Field(default_factory=list)
    witnesses: int = 0


class RecordLine(ContextItem):
    id: int
    age: int
    text: str
    how: str | None = None


class EventRecordsContext(PromptContext):
    title: str
    accounts: list[RecordLine] = Field(default_factory=list)
    more_accounts: int = 0
    steps: list[RecordLine] = Field(default_factory=list)
    more_steps: int = 0
    changes: list[RecordLine] = Field(default_factory=list)
    more_changes: int = 0
    tool: str
