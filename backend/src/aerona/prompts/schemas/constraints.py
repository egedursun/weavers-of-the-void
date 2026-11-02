from dataclasses import dataclass
from typing import Any

JsonSchema = dict[str, Any]
SchemaPath = tuple[str, ...]
ITEMS = "[]"


@dataclass(frozen=True)
class ArrayBounds:
    path: SchemaPath
    min_items: int | None = None
    max_items: int | None = None


@dataclass(frozen=True)
class NumberBounds:
    path: SchemaPath
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True)
class EnumValues:
    path: SchemaPath
    values: tuple[str | int, ...]


@dataclass(frozen=True)
class StringLength:
    path: SchemaPath
    min_length: int


@dataclass(frozen=True)
class OmitField:
    path: SchemaPath


@dataclass(frozen=True)
class RequireField:
    path: SchemaPath


@dataclass(frozen=True)
class ObjectFields:
    path: SchemaPath
    fields: tuple[tuple[str, str], ...]


Constraint = ArrayBounds | NumberBounds | EnumValues | StringLength | OmitField | RequireField | ObjectFields


class SchemaPathError(KeyError):
    pass


def concrete(node: JsonSchema) -> JsonSchema:
    variants = node.get("anyOf")
    if isinstance(variants, list):
        for variant in variants:
            if isinstance(variant, dict) and variant.get("type") != "null":
                return variant
    return node


def resolve(schema: JsonSchema, path: SchemaPath) -> JsonSchema:
    node = concrete(schema)
    for step in path:
        child = node.get("items") if step == ITEMS else node.get("properties", {}).get(step)
        if not isinstance(child, dict):
            raise SchemaPathError("/".join(path))
        node = concrete(child)
    return node


def parent_and_key(schema: JsonSchema, path: SchemaPath) -> tuple[JsonSchema, str]:
    if not path or path[-1] == ITEMS:
        raise SchemaPathError("/".join(path))
    return resolve(schema, path[:-1]), path[-1]


def set_present(node: JsonSchema, values: dict[str, object]) -> None:
    node.update({key: value for key, value in values.items() if value is not None})


def apply_array_bounds(schema: JsonSchema, constraint: ArrayBounds) -> None:
    set_present(resolve(schema, constraint.path), {"minItems": constraint.min_items, "maxItems": constraint.max_items})


def apply_number_bounds(schema: JsonSchema, constraint: NumberBounds) -> None:
    set_present(resolve(schema, constraint.path), {"minimum": constraint.minimum, "maximum": constraint.maximum})


def apply_enum(schema: JsonSchema, constraint: EnumValues) -> None:
    resolve(schema, constraint.path)["enum"] = list(constraint.values)


def apply_string_length(schema: JsonSchema, constraint: StringLength) -> None:
    resolve(schema, constraint.path)["minLength"] = constraint.min_length


def apply_omit(schema: JsonSchema, constraint: OmitField) -> None:
    parent, key = parent_and_key(schema, constraint.path)
    parent.get("properties", {}).pop(key, None)
    required = parent.get("required")
    if isinstance(required, list) and key in required:
        required.remove(key)


def apply_require(schema: JsonSchema, constraint: RequireField) -> None:
    parent, key = parent_and_key(schema, constraint.path)
    required = parent.setdefault("required", [])
    if key not in required:
        required.append(key)


def apply_object_fields(schema: JsonSchema, constraint: ObjectFields) -> None:
    parent, key = parent_and_key(schema, constraint.path)
    description = parent.get("properties", {}).get(key, {}).get("description")
    replacement: JsonSchema = {
        "type": "object",
        "properties": {name: {"type": "string", "description": text} for name, text in constraint.fields},
        "required": [name for name, _ in constraint.fields],
    }
    if description:
        replacement["description"] = description
    parent.setdefault("properties", {})[key] = replacement


def apply_constraint(schema: JsonSchema, constraint: Constraint) -> None:
    match constraint:
        case ArrayBounds():
            apply_array_bounds(schema, constraint)
        case NumberBounds():
            apply_number_bounds(schema, constraint)
        case EnumValues():
            apply_enum(schema, constraint)
        case StringLength():
            apply_string_length(schema, constraint)
        case OmitField():
            apply_omit(schema, constraint)
        case RequireField():
            apply_require(schema, constraint)
        case ObjectFields():
            apply_object_fields(schema, constraint)
