import json
from typing import Any

import pytest
from pydantic import ValidationError

from aerona.prompts import PROMPTS, PromptId, output_model, output_schema, validate_output
from aerona.prompts.errors import PromptOutputMissingError
from aerona.prompts.schemas.constraints import (
    ITEMS,
    ArrayBounds,
    EnumValues,
    NumberBounds,
    ObjectFields,
    OmitField,
    RequireField,
    SchemaPathError,
    StringLength,
)
from aerona.prompts.schemas.descriptions import image_prompt_rules
from aerona.rules.registry import Rules
from tests.prompts.payloads import PAYLOADS

RULES = Rules()
STRUCTURED = [prompt for prompt, spec in PROMPTS.items() if spec.output is not None]


def walk(node: Any, path: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], dict[str, Any]]]:
    found: list[tuple[tuple[str, ...], dict[str, Any]]] = []
    if isinstance(node, dict):
        found.append((path, node))
        for key, value in node.items():
            found.extend(walk(value, (*path, key)))
    elif isinstance(node, list):
        for item in node:
            found.extend(walk(item, path))
    return found


def test_every_structured_prompt_has_a_payload() -> None:
    assert set(PAYLOADS) == set(STRUCTURED)


@pytest.mark.parametrize("prompt_id", STRUCTURED)
def test_output_validates_its_sample_payload(prompt_id: PromptId) -> None:
    parsed = validate_output(prompt_id, PAYLOADS[prompt_id])
    assert isinstance(parsed, output_model(prompt_id))


@pytest.mark.parametrize("prompt_id", STRUCTURED)
def test_output_schema_is_self_contained_and_rendered(prompt_id: PromptId) -> None:
    schema = output_schema(prompt_id, RULES)
    dumped = json.dumps(schema)
    assert "$ref" not in dumped
    assert "$defs" not in dumped
    assert "{{" not in dumped
    assert schema["type"] == "object"


@pytest.mark.parametrize("prompt_id", STRUCTURED)
def test_image_prompt_fields_carry_the_image_rules(prompt_id: PromptId) -> None:
    rules_text = image_prompt_rules()
    for path, node in walk(output_schema(prompt_id, RULES)):
        properties = node.get("properties")
        if (path and path[-1] == "properties") or not isinstance(properties, dict):
            continue
        image = properties.get("image_prompt")
        if isinstance(image, dict):
            assert rules_text in image.get("description", ""), (prompt_id, path)


def test_default_constraints_follow_live_rules() -> None:
    schema = output_schema(PromptId.GENESIS_USER, RULES)
    regions = schema["properties"]["regions"]
    assert regions["minItems"] == RULES.genesis.regions_min
    assert regions["maxItems"] == RULES.genesis.regions_max
    chat = output_schema(PromptId.SON_CHAT_USER, RULES)["properties"]["loyalty_change"]
    assert chat["maximum"] == RULES.council.chat_loyalty_max_change
    assert chat["minimum"] == -RULES.council.chat_loyalty_max_change
    rationale = output_schema(PromptId.FATE_EXTRA_JUDGMENT_USER, RULES)["properties"]["verdicts"]["items"]["properties"]["rationale"]
    assert f"at most {RULES.fate.reason_max_words} words" in rationale["description"]


def test_runtime_constraints_shape_the_schema() -> None:
    schema = output_schema(
        PromptId.FATE_JUDGMENT_USER,
        RULES,
        [
            OmitField(("resolved_story",)),
            ArrayBounds(("closed_stories",), min_items=2),
            ArrayBounds(("new_stories",), max_items=1),
            EnumValues(("words", ITEMS, "language_id"), (20, 21)),
            RequireField(("facts",)),
            StringLength(("verdicts", ITEMS, "rationale"), 5),
            NumberBounds(("rewards", ITEMS, "fame"), 1, 3),
        ],
    )
    properties = schema["properties"]
    assert "resolved_story" not in properties
    assert properties["closed_stories"]["minItems"] == 2
    assert properties["new_stories"]["maxItems"] == 1
    assert properties["words"]["items"]["properties"]["language_id"]["enum"] == [20, 21]
    assert "facts" in schema["required"]
    assert properties["rewards"]["items"]["properties"]["fame"]["maximum"] == 3


def test_object_fields_and_variables() -> None:
    schema = output_schema(PromptId.DEEPEN_ENTITY_USER, RULES, [ObjectFields(("special",), (("temperament", "Temperament"),))])
    special = schema["properties"]["special"]
    assert special["required"] == ["temperament"]
    foreign = output_schema(PromptId.FOREIGN_GOD_DEEPEN_USER, RULES, variables={"foreign_god_powers": "«every power»"})
    assert "«every power»" in foreign["properties"]["powers"]["description"]


def test_bad_paths_and_missing_outputs_raise() -> None:
    with pytest.raises(SchemaPathError):
        output_schema(PromptId.SON_CHAT_USER, RULES, [ArrayBounds(("nothing",), 1, 2)])
    with pytest.raises(PromptOutputMissingError):
        output_model(PromptId.WORLD_HEADER)


def test_invalid_payload_is_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_output(PromptId.SON_CHAT_USER, {"reply": "x", "attitude": "bored", "loyalty_change": 1})
