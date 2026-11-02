from enum import StrEnum

from aerona.prompts.contexts.base import PromptContext


class SignKind(StrEnum):
    WRATH = "wrath"
    GRACE = "grace"
    SILENCE = "silence"
    LONELINESS = "loneliness"
    ESTRANGED = "estranged"


class CreatorSignContext(PromptContext):
    kind: SignKind
    variant: int = 0
    creator: str
    place: str = ""
    disaster: str = ""
    subject: str = ""


class SentientDemandContext(PromptContext):
    resource: str
    owner: str
    demand_variant: int = 0
    paid: bool
    new_owner: str | None = None
