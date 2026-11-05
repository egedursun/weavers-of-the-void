import re
from enum import Enum
from types import NoneType, UnionType
from typing import Annotated, Any, Literal, Union, get_args, get_origin

from pydantic import BaseModel, ConfigDict, model_validator

from aerona.catalog.choice_synonyms import BOND_SYNONYMS, TRAIT_SYNONYMS
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.mind import TraitKind

ID_PATTERN = re.compile(r"^\s*(?:[A-Za-z_ ]{0,20}#|id\s+)?\s*(-?\d+)\s*$", re.IGNORECASE)
DECIMAL_COMMA = re.compile(r"^\s*-?\d+,\d+\s*$")
SEPARATORS = re.compile(r"[\s_\-]+")
EMPTY_MARKERS = frozenset({"", "#0", "none", "null", "undefined", "-", "nothing", "nil"})
PREFIX_MATCH_MIN = 3
ABSENT = object()


def is_identity_field(name: str) -> bool:
    return name == "id" or name.endswith("_id") or name.endswith("_ids")


def _unwrap(annotation: Any) -> list[Any]:
    origin = get_origin(annotation)
    if origin is Annotated:
        return _unwrap(get_args(annotation)[0])
    if origin in (Union, UnionType):
        return [inner for arg in get_args(annotation) if arg is not NoneType for inner in _unwrap(arg)]
    return [annotation]


def _sequence_item(annotation: Any) -> Any | None:
    for candidate in _unwrap(annotation):
        if get_origin(candidate) in (list, tuple, set, frozenset):
            args = get_args(candidate)
            return args[0] if args else Any
    return None


def choices_of(annotation: Any) -> list[str] | None:
    for candidate in _unwrap(annotation):
        if get_origin(candidate) is Literal:
            return [str(value) for value in get_args(candidate)]
        if isinstance(candidate, type) and issubclass(candidate, Enum):
            return [str(member.value) for member in candidate]
    return None


def is_numeric(annotation: Any) -> bool:
    return any(candidate in (int, float) for candidate in _unwrap(annotation))


def fold_choice(text: str) -> str:
    return SEPARATORS.sub(" ", text.strip().casefold()).strip()


def match_choice(value: str, choices: list[str]) -> str | None:
    wanted = fold_choice(value)
    folded = {fold_choice(choice): choice for choice in choices}
    if wanted in folded:
        return folded[wanted]
    if len(wanted) < PREFIX_MATCH_MIN:
        return None
    starts = [choice for key, choice in folded.items() if key.startswith(wanted)]
    return starts[0] if len(starts) == 1 else None


def _identity_text(value: str, optional: bool) -> Any:
    text = value.strip()
    if text.casefold() in EMPTY_MARKERS:
        return ABSENT
    found = ID_PATTERN.match(text)
    if found is None:
        return value
    number = int(found.group(1))
    return ABSENT if optional and number == 0 else number


def clean_identity(value: Any, optional: bool) -> Any:
    if value is None:
        return ABSENT
    if isinstance(value, str):
        return _identity_text(value, optional)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return ABSENT if optional and value == 0 else value
    return value


def clean_number(value: Any) -> Any:
    if isinstance(value, str):
        text = value.strip().rstrip("%").strip()
        if DECIMAL_COMMA.match(text):
            return text.replace(",", ".")
        found = ID_PATTERN.match(text)
        return found.group(1) if found is not None and "#" in text else text
    return value


def synonyms_of(annotation: Any) -> dict[str, str]:
    for candidate in _unwrap(annotation):
        if candidate is BondKind:
            return {fold_choice(word): kind.value for word, kind in BOND_SYNONYMS.items()}
        if candidate is TraitKind:
            return {fold_choice(word): kind.value for word, kind in TRAIT_SYNONYMS.items()}
    return {}


def clean_choice(value: Any, choices: list[str], synonyms: dict[str, str] | None = None) -> Any:
    if isinstance(value, str):
        matched = match_choice(value, choices)
        if matched is None and synonyms:
            matched = synonyms.get(fold_choice(value))
        return matched if matched is not None else value
    return value


def clean_scalar(name: str, annotation: Any, value: Any, optional: bool) -> Any:
    if is_identity_field(name):
        return clean_identity(value, optional)
    if optional and isinstance(value, str) and value.strip().casefold() in EMPTY_MARKERS:
        return ABSENT
    if value is None and optional:
        return ABSENT
    choices = choices_of(annotation)
    if choices is not None:
        return clean_choice(value, choices, synonyms_of(annotation))
    if is_numeric(annotation):
        return clean_number(value)
    return value


def clean_field(name: str, annotation: Any, value: Any, optional: bool) -> Any:
    item = _sequence_item(annotation)
    if item is None:
        return clean_scalar(name, annotation, value, optional)
    if value is None or (isinstance(value, str) and value.strip().casefold() in EMPTY_MARKERS):
        return ABSENT if optional else value
    items = value if isinstance(value, (list, tuple)) else [value]
    cleaned = [clean_scalar(name, item, element, True) for element in items]
    return [element for element in cleaned if element is not ABSENT]


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    @model_validator(mode="before")
    @classmethod
    def _sanitise(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        cleaned: dict[str, Any] = {}
        for key, value in data.items():
            field = cls.model_fields.get(key)
            if field is None:
                cleaned[key] = value
                continue
            result = clean_field(key, field.annotation, value, not field.is_required())
            if result is not ABSENT:
                cleaned[key] = result
        return cleaned


class EmptyInput(ToolInput):
    pass
