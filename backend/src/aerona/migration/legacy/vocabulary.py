import json
from enum import StrEnum
from functools import cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_MAP_PATH = Path(__file__).resolve().parent / "schema_map.json"


class LegacyTable(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    required: tuple[str, ...] = ()
    columns: dict[str, str]

    def physical(self, column: str) -> str:
        return self.columns[column]


class TagVocabulary(BaseModel):
    model_config = ConfigDict(frozen=True)

    prefixes: dict[str, str]
    war_ongoing: str
    war_ended: str
    standby: str
    captive: str
    flags: dict[str, str]
    flag_variants: dict[str, str] = Field(default_factory=dict)
    system_kept: tuple[str, ...] = ()


class MortalRoleVocabulary(BaseModel):
    model_config = ConfigDict(frozen=True)

    subtypes: dict[str, str]
    tags: dict[str, str]


class TextVocabulary(BaseModel):
    model_config = ConfigDict(frozen=True)

    closed_prefix: str
    overdue_marker: str
    debt_pattern: str
    debt_format: str
    truce_pattern: str
    truce_format: str
    engine_prefix: str
    pending_job_key: str
    domain_separator: str


class PatternVocabulary(BaseModel):
    model_config = ConfigDict(frozen=True)

    water: str
    dry: str
    underworld: str
    temple: str
    legend_categories: tuple[tuple[str, str], ...]
    journey_events: tuple[tuple[str, str], ...]


class Vocabulary(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: int
    source: str
    database_file: str
    image_directory: str
    thumbnail_directory: str
    tables: dict[str, LegacyTable]
    node_codes: dict[str, str]
    enums: dict[str, dict[str, str]]
    engine_kinds: dict[str, dict[str, str]]
    engine_kind_tags: dict[str, str]
    species_classes: dict[str, str] = Field(default_factory=dict)
    mortal_roles: MortalRoleVocabulary
    tags: TagVocabulary
    bond_roles: dict[str, dict[str, str]]
    texts: TextVocabulary
    patterns: PatternVocabulary
    canon_predicates: dict[str, str]
    json_keys: dict[str, dict[str, str]]
    entity_stats: dict[str, dict[str, str]]
    entity_extra_stats: dict[str, str]
    rules: dict[str, str | None] = Field(default_factory=dict)
    rules_unmapped: tuple[str, ...] = ()

    def table(self, name: str) -> LegacyTable:
        return self.tables[name]

    def code(self, node_kind: str) -> str:
        return self.node_codes[node_kind]

    def node_kind_of(self, code: str | None) -> str | None:
        if code is None:
            return None
        return next((kind for kind, value in self.node_codes.items() if value == code), None)

    def decode(self, enum_name: str, value: Any) -> str | None:
        if value is None:
            return None
        table = self.enums[enum_name]
        text = str(value).strip()
        if text in table:
            return table[text]
        folded = text.casefold()
        return next((english for legacy, english in table.items() if legacy.casefold() == folded), None)

    def decode_as[E: StrEnum](self, enum_name: str, value: Any, kind: type[E]) -> E | None:
        english = self.decode(enum_name, value)
        if english is None:
            return None
        try:
            return kind(english)
        except ValueError:
            return None

    def encode(self, enum_name: str, english: str) -> str:
        table = self.enums[enum_name]
        return next(legacy for legacy, value in table.items() if value == english)

    def key(self, shape: str, english: str) -> str:
        return self.json_keys[shape][english]

    def field(self, shape: str, payload: Any, english: str) -> Any:
        if not isinstance(payload, dict):
            return None
        return payload.get(self.key(shape, english))

    def prefix(self, english: str) -> str:
        return self.tags.prefixes[english]


@cache
def load_vocabulary(path: Path = SCHEMA_MAP_PATH) -> Vocabulary:
    return Vocabulary.model_validate(json.loads(path.read_text(encoding="utf-8")))
