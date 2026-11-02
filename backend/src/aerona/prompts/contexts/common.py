from pydantic import Field

from aerona.prompts.contexts.base import ContextItem


class EntityLineItem(ContextItem):
    id: int
    name: str
    type_label: str
    subtype: str | None = None
    power_level: int
    location: str | None = None
    status_label: str | None = None


class WorldItem(ContextItem):
    id: int
    name: str


class SonBrief(ContextItem):
    id: int
    name: str
    title: str | None = None
    domain_1: str
    domain_2: str


class MotifShare(ContextItem):
    key: str
    percent: int


class ChronicleRow(ContextItem):
    age: int
    text: str


class LexiconWord(ContextItem):
    word: str
    meaning: str
    kind: str | None = None


class NamedRecord(ContextItem):
    id: int
    name: str


class LabelValue(ContextItem):
    label: str
    value: str


class TiredImages(ContextItem):
    motifs: list[MotifShare] = Field(default_factory=list)
    foreign_images: list[str] = Field(default_factory=list)

    @property
    def present(self) -> bool:
        return bool(self.motifs or self.foreign_images)


class NamingRuleItem(ContextItem):
    vowels: str = ""
    consonants: str = ""
    forbidden_sounds: list[str] = Field(default_factory=list)
    syllable_patterns: list[str] = Field(default_factory=list)
    endings: list[str] = Field(default_factory=list)
    sample_names: list[str] = Field(default_factory=list)
