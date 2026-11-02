import copy
from collections.abc import Mapping, Sequence
from typing import Any

from aerona.prompts.environment import string_template
from aerona.prompts.schemas.base import OutputModel
from aerona.prompts.schemas.constraints import Constraint, JsonSchema, apply_constraint
from aerona.prompts.schemas.descriptions import description_variables
from aerona.rules.registry import Rules

REFERENCE_PREFIX = "#/$defs/"
DROPPED_KEYS = frozenset({"title", "default"})
TEMPLATE_MARKER = "{{"


def inline_references(node: Any, definitions: Mapping[str, Any]) -> Any:
    if isinstance(node, dict):
        reference = node.get("$ref")
        if isinstance(reference, str) and reference.startswith(REFERENCE_PREFIX):
            target = copy.deepcopy(definitions[reference.removeprefix(REFERENCE_PREFIX)])
            merged = {**target, **{key: value for key, value in node.items() if key != "$ref"}}
            return inline_references(merged, definitions)
        return {key: inline_references(value, definitions) for key, value in node.items() if key != "$defs"}
    if isinstance(node, list):
        return [inline_references(item, definitions) for item in node]
    return node


def strip_metadata(node: Any) -> Any:
    if isinstance(node, dict):
        cleaned: dict[str, Any] = {}
        for key, value in node.items():
            if key in DROPPED_KEYS and not isinstance(value, dict):
                continue
            if key == "properties" and isinstance(value, dict):
                cleaned[key] = {name: strip_metadata(child) for name, child in value.items()}
            else:
                cleaned[key] = strip_metadata(value)
        return cleaned
    if isinstance(node, list):
        return [strip_metadata(item) for item in node]
    return node


def render_descriptions(node: Any, variables: Mapping[str, object]) -> Any:
    if isinstance(node, dict):
        rendered: dict[str, Any] = {}
        for key, value in node.items():
            if key == "description" and isinstance(value, str) and TEMPLATE_MARKER in value:
                rendered[key] = string_template(value).render(**variables).strip()
            elif key == "properties" and isinstance(value, dict):
                rendered[key] = {name: render_descriptions(child, variables) for name, child in value.items()}
            else:
                rendered[key] = render_descriptions(value, variables)
        return rendered
    if isinstance(node, list):
        return [render_descriptions(item, variables) for item in node]
    return node


def build_json_schema(
    model: type[OutputModel],
    rules: Rules,
    constraints: Sequence[Constraint] = (),
    variables: Mapping[str, object] | None = None,
) -> JsonSchema:
    raw = model.model_json_schema()
    inlined = inline_references(raw, raw.get("$defs", {}))
    schema: JsonSchema = render_descriptions(strip_metadata(inlined), {**description_variables(rules), **(variables or {})})
    for constraint in constraints:
        apply_constraint(schema, constraint)
    return schema
