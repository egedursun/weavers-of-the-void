from pydantic import Field

from aerona.domain.enums.son import ExistenceMode
from aerona.domain.models.base import ValueObject


class Personality(ValueObject):
    appearance: str = ""
    temperament: str = ""
    obsession: str = ""
    fear: str = ""
    speech_style: str = ""
    secret: str = ""


class ExistenceProfile(ValueObject):
    nature: str = ""
    mode: ExistenceMode | None = None
    manifestation: str = ""
    true_name: str = ""


class Saying(ValueObject):
    form: str
    text: str


class EntityDepth(ValueObject):
    history: str = ""
    rumours: tuple[str, ...] = ()
    sayings: tuple[Saying, ...] = ()
    details: tuple[str, ...] = ()
    hidden_truth: str = ""
    specifics: dict[str, str] = Field(default_factory=dict)
    epoch: int = Field(ge=0)


class GodName(ValueObject):
    name: str
    used_by: str = ""
    meaning: str = ""


class GodDepth(ValueObject):
    history: str = ""
    names: tuple[GodName, ...] = ()
    secrets: tuple[str, ...] = ()
    fears: tuple[str, ...] = ()
    taboos: tuple[str, ...] = ()
    gifts: tuple[str, ...] = ()
    desire: str = ""
    sayings: tuple[Saying, ...] = ()
    rumours: tuple[str, ...] = ()
    hidden_truth: str = ""
    view_of_pantheon: str = ""
    worship: str = ""
    epoch: int = Field(ge=0)


class EpicChapter(ValueObject):
    title: str
    text: str
    epoch_start: int = Field(ge=0)
    epoch_end: int = Field(ge=0)


class Epic(ValueObject):
    title: str
    verse: str = ""
    body: str = ""
    chapters: tuple[EpicChapter, ...] = ()
    epoch: int = Field(ge=0)


class TravelResource(ValueObject):
    name: str
    description: str = ""
    rule: str = ""
    side_effect: str = ""
