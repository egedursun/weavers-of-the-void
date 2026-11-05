import copy
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ValidationError
from pydantic_core import ErrorDetails

from aerona.prompts import PromptId, render
from aerona.prompts.contexts.agent import FieldErrorContext, FieldErrorKind
from aerona.prompts.tools.results import CommonResult, result
from aerona.tools.framework.inputs import _sequence_item, _unwrap, choices_of, fold_choice, is_numeric

REFERENCE_PREFIX = "#/$defs/"
NUMBER_TYPES = frozenset({"int_parsing", "float_parsing", "int_from_float", "int_type", "float_type", "greater_than_equal", "less_than_equal"})
NUMERIC_JSON_TYPES = ("integer", "number")
PREFIX_BONUS_LETTERS = 2


def _inline(node: Any, definitions: Mapping[str, Any]) -> Any:
    if isinstance(node, dict):
        reference = node.get("$ref")
        if isinstance(reference, str) and reference.startswith(REFERENCE_PREFIX):
            resolved = copy.deepcopy(definitions[reference.removeprefix(REFERENCE_PREFIX)])
            merged = {**_inline(resolved, definitions), **{key: value for key, value in node.items() if key != "$ref"}}
            return merged
        return {key: _inline(value, definitions) for key, value in node.items() if key != "title"}
    if isinstance(node, list):
        return [_inline(item, definitions) for item in node]
    return node


def _describe(node: Any, path: str, fields: Mapping[str, str]) -> None:
    if not isinstance(node, dict):
        return
    for name, child in node.get("properties", {}).items():
        key = f"{path}.{name}" if path else name
        if key in fields and isinstance(child, dict):
            child["description"] = fields[key]
        _descend(child, key, fields)


def _descend(node: Any, path: str, fields: Mapping[str, str]) -> None:
    if not isinstance(node, dict):
        return
    _describe(node, path, fields)
    if "items" in node:
        _descend(node["items"], path, fields)
    for variant in node.get("anyOf", []):
        _descend(variant, path, fields)


def _loosen(node: Any) -> None:
    if isinstance(node, dict):
        if node.get("type") in NUMERIC_JSON_TYPES:
            node["type"] = [node["type"], "string"]
        if "enum" in node and node.get("type", "string") == "string":
            choices = node.pop("enum")
            node.pop("type", None)
            node["anyOf"] = [{"type": "string", "enum": choices}, {"type": "string"}]
            return
        for value in node.values():
            _loosen(value)
    elif isinstance(node, list):
        for item in node:
            _loosen(item)


def input_schema(model: type[BaseModel], fields: Mapping[str, str]) -> dict[str, Any]:
    raw = model.model_json_schema()
    definitions = raw.pop("$defs", {})
    schema: dict[str, Any] = _inline(raw, definitions)
    schema.setdefault("properties", {})
    schema["type"] = "object"
    _describe(schema, "", fields)
    _loosen(schema)
    return schema


def field_path(error: ErrorDetails) -> str:
    return ".".join(str(part) for part in error["loc"] if not isinstance(part, int))


def _limit(error: ErrorDetails, *keys: str) -> Any:
    context = error.get("ctx") or {}
    for key in keys:
        if key in context:
            return context[key]
    return None


def _given(error: ErrorDetails) -> str:
    value = error.get("input")
    return "" if value is None else str(value)


def _number_error(error: ErrorDetails, field: str) -> str:
    kind_of = {
        "missing": FieldErrorKind.MISSING,
        "greater_than_equal": FieldErrorKind.TOO_SMALL,
        "greater_than": FieldErrorKind.TOO_SMALL,
        "less_than_equal": FieldErrorKind.TOO_BIG,
        "less_than": FieldErrorKind.TOO_BIG,
        "int_from_float": FieldErrorKind.NOT_INTEGER,
    }
    kind = kind_of.get(error["type"], FieldErrorKind.NOT_NUMBER)
    limit = _limit(error, "ge", "gt", "le", "lt")
    return render(PromptId.FIELD_ERROR, FieldErrorContext(kind=kind, field=field, limit=float(limit) if limit is not None else None, given=_given(error)))


def edit_distance(first: str, second: str) -> int:
    previous = list(range(len(second) + 1))
    for row, left in enumerate(first, start=1):
        current = [row]
        for column, right in enumerate(second, start=1):
            current.append(min(previous[column] + 1, current[column - 1] + 1, previous[column - 1] + (left != right)))
        previous = current
    return previous[-1]


def nearest_choices(choices: list[str], given: str, count: int) -> list[str]:
    wanted = fold_choice(given)

    def score(choice: str) -> tuple[int, str]:
        folded = fold_choice(choice)
        bonus = 1 if wanted and folded.startswith(wanted[:PREFIX_BONUS_LETTERS]) else 0
        return edit_distance(wanted, folded) - bonus, choice

    return sorted(choices, key=score)[: max(1, count)]


def _choices(model: type[BaseModel], error: ErrorDetails) -> list[str] | None:
    current: Any = model
    for part in error["loc"]:
        if isinstance(part, int):
            item = _sequence_item(current)
            current = item if item is not None else current
            continue
        nested = next((candidate for candidate in _unwrap(current) if isinstance(candidate, type) and issubclass(candidate, BaseModel)), None)
        if nested is None:
            item = _sequence_item(current)
            nested = item if isinstance(item, type) and issubclass(item, BaseModel) else None
        if nested is None:
            return None
        field = nested.model_fields.get(str(part))
        if field is None:
            return None
        current = field.annotation
    return choices_of(current)


def _is_number_field(model: type[BaseModel], error: ErrorDetails) -> bool:
    if error["type"] in NUMBER_TYPES:
        return True
    if error["type"] != "missing":
        return False
    current: Any = model
    for part in error["loc"]:
        if isinstance(part, int) or not (isinstance(current, type) and issubclass(current, BaseModel)):
            continue
        field = current.model_fields.get(str(part))
        if field is None:
            return False
        current = field.annotation
    return is_numeric(current)


LIMITED_ERRORS = {
    "string_too_short": (CommonResult.TEXT_TOO_SHORT, "min_length"),
    "string_too_long": (CommonResult.TEXT_TOO_LONG, "max_length"),
    "too_short": (CommonResult.LIST_TOO_SHORT, "min_length"),
    "too_long": (CommonResult.LIST_TOO_LONG, "max_length"),
}
CHOICE_ERRORS = frozenset({"enum", "literal_error"})


def describe_validation_error(model: type[BaseModel], error: ValidationError, hints: int) -> str:
    first = error.errors()[0]
    field = field_path(first) or model.__name__
    kind = first["type"]
    if _is_number_field(model, first):
        return _number_error(first, field)
    if kind == "missing":
        return result(CommonResult.FIELD_MISSING, field=field)
    if kind in LIMITED_ERRORS:
        template, key = LIMITED_ERRORS[kind]
        return result(template, field=field, limit=_limit(first, key))
    if kind in CHOICE_ERRORS:
        choices = _choices(model, first)
        if choices and len(choices) > hints:
            nearest = nearest_choices(choices, _given(first), hints)
            return result(CommonResult.NEAREST_CHOICE, field=field, choices=", ".join(nearest), total=len(choices), given=_given(first))
        return result(CommonResult.INVALID_CHOICE, field=field, choices=_limit(first, "expected") or "", given=_given(first))
    return result(CommonResult.INVALID_FIELD, field=field, detail=first["msg"])
