from typing import Any

import jinja2.meta
import jsonschema
import pytest
from pydantic import BaseModel

from aerona.domain.enums.ecology import Sociality
from aerona.prompts import MortalToolId, SonToolId, tool_text
from aerona.prompts.environment import environment
from aerona.prompts.tools.context import ToolTextContext
from aerona.prompts.tools.results import CommonResult, MortalResult, SonResult, result
from aerona.rules.registry import Rules
from aerona.tools.framework.inputs import ToolInput, _sequence_item, _unwrap
from aerona.tools.framework.schema import input_schema
from aerona.tools.mortal.registry import mortal_specs
from aerona.tools.son.registry import son_specs

RULES = Rules()
CONTEXT = ToolTextContext(power_ceiling=5, example_cost=7)
SPECS: list[Any] = [*son_specs(), *mortal_specs()]


def _nested(annotation: Any) -> type[BaseModel] | None:
    item = _sequence_item(annotation)
    for candidate in _unwrap(item if item is not None else annotation):
        if isinstance(candidate, type) and issubclass(candidate, ToolInput):
            return candidate
    return None


def field_paths(model: type[BaseModel], prefix: str = "") -> list[str]:
    paths: list[str] = []
    for name, field in model.model_fields.items():
        path = f"{prefix}{name}"
        paths.append(path)
        nested = _nested(field.annotation)
        if nested is not None:
            paths.extend(field_paths(nested, f"{path}."))
    return paths


def test_every_son_tool_has_exactly_one_spec() -> None:
    names = [spec.name for spec in son_specs()]
    assert sorted(names) == sorted(tool.value for tool in SonToolId)


def test_every_mortal_tool_has_exactly_one_spec() -> None:
    names = [spec.name for spec in mortal_specs()]
    assert sorted(names) == sorted(tool.value for tool in MortalToolId)


@pytest.mark.parametrize("spec", SPECS, ids=lambda spec: f"{spec.agent.value}.{spec.name}")
def test_input_fields_are_described_by_the_prompt_catalog(spec: Any) -> None:
    tool_id = SonToolId(spec.name) if spec.agent.value == "son" else MortalToolId(spec.name)
    text = tool_text(tool_id, RULES, CONTEXT)
    missing = [path for path in field_paths(spec.input_model) if path not in text.fields]
    assert not missing
    schema = input_schema(spec.input_model, text.fields)
    assert schema["type"] == "object"
    assert "$defs" not in str(schema.keys())
    assert closed_choices(schema) == [], "a field with fixed choices must still let loose spellings reach the tool's own matcher"


def closed_choices(node: Any, path: str = "", loose: bool = False) -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        options = node.get("anyOf") or []
        open_text = any(isinstance(option, dict) and option.get("type") == "string" and "enum" not in option for option in options)
        if "enum" in node and not loose:
            found.append(path)
        for key, value in node.items():
            found.extend(closed_choices(value, f"{path}.{key}", loose=open_text if key == "anyOf" else False))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            found.extend(closed_choices(item, f"{path}[{index}]", loose=loose))
    return found


class LooseChoice(ToolInput):
    sociality: Sociality | None = None


def test_loose_spellings_and_empty_markers_pass_the_sdk_schema_and_reach_the_matcher() -> None:
    schema = input_schema(LooseChoice, {"sociality": "How it lives"})
    for given, expected in (("PACK", Sociality.PACK), ("Herd", Sociality.HERD), ("none", None)):
        jsonschema.validate(instance={"sociality": given}, schema=schema)
        assert LooseChoice.model_validate({"sociality": given}).sociality is expected


@pytest.mark.parametrize("spec", SPECS, ids=lambda spec: f"{spec.agent.value}.{spec.name}")
def test_metadata_is_explicit(spec: Any) -> None:
    meta = spec.meta
    assert meta.actions(RULES) >= 0
    assert meta.essence(RULES) >= 0
    if meta.read_only:
        assert meta.actions(RULES) == 0


@pytest.mark.parametrize("spec", SPECS, ids=lambda spec: f"{spec.agent.value}.{spec.name}")
def test_power_level_is_bounded_only_by_the_rarity_ceiling(spec: Any) -> None:
    power = spec.input_model.model_json_schema().get("properties", {}).get("power_level", {})
    assert "maximum" not in power and "exclusiveMaximum" not in power


@pytest.mark.parametrize("template", [*CommonResult, *SonResult, *MortalResult], ids=lambda template: f"{type(template).__name__}.{template.name}")
def test_every_result_text_renders(template: Any) -> None:
    names = jinja2.meta.find_undeclared_variables(environment().parse(template.value))
    text = result(template, **dict.fromkeys(names, "7"))
    assert text
    assert "{{" not in text


def test_rarity_gates_follow_rules() -> None:
    by_name = {spec.name: spec for spec in son_specs()}
    assert by_name["birth_world"].meta.minimum_rarity(RULES) is not None
    assert by_name["world_summary"].meta.minimum_rarity(RULES) is None
    assert by_name["create_region"].meta.minimum_rarity(RULES).rank > by_name["create_place"].meta.minimum_rarity(RULES).rank
