from dataclasses import replace
from typing import cast

import pytest

from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.prompts import MortalToolId, SonToolId, tool_description, tool_text
from aerona.prompts.contexts.cosmos import StarLine
from aerona.prompts.errors import UnknownToolError
from aerona.prompts.tools.context import ToolTextContext
from aerona.prompts.tools.mortal import MORTAL_TOOL_TEXTS
from aerona.prompts.tools.son import CREATION_TOOLS, SON_TOOL_TEXTS
from aerona.rules.registry import Rules

RULES = Rules()


def test_every_tool_id_has_a_text() -> None:
    assert set(SON_TOOL_TEXTS) == set(SonToolId)
    assert set(MORTAL_TOOL_TEXTS) == set(MortalToolId)


def test_creation_tools_match_the_catalog() -> None:
    catalog_tools = {spec.creation_tool for spec in ENTITY_TYPES.values() if spec.creation_tool}
    assert {tool.value for tool in CREATION_TOOLS} == catalog_tools


@pytest.mark.parametrize("tool_id", [*SonToolId, *MortalToolId])
def test_every_tool_text_renders(tool_id: SonToolId | MortalToolId) -> None:
    rendered = tool_text(tool_id, RULES, ToolTextContext(power_ceiling=5, example_cost=7, stars=[StarLine(id=1, name="Ka", type_label="Yellow dwarf")]))
    assert rendered.description
    for text in (rendered.description, *rendered.fields.values()):
        assert "{{" not in text
        assert "{%" not in text
        assert "None" not in text


def test_descriptions_render_live_rule_values() -> None:
    changed = replace(RULES, son_tools=replace(RULES.son_tools, covenant_min_relation=77))
    assert "77" in tool_description(SonToolId.SWEAR_COVENANT, changed)
    assert str(RULES.son_tools.covenant_min_relation) in tool_description(SonToolId.SWEAR_COVENANT, RULES)
    cheaper = replace(RULES, son_tools=replace(RULES.son_tools, intervention_cost_pct=200))
    assert "Cost: 30 + power level essence" in tool_description(SonToolId.MIRACLE, cheaper)


def test_creation_tool_text_carries_type_details() -> None:
    rendered = tool_text(SonToolId.CREATE_PEOPLE, RULES, ToolTextContext(power_ceiling=6, example_cost=4))
    assert rendered.description.startswith("Creates a People")
    assert "about 4 essence" in rendered.description
    assert "your ceiling is 6" in rendered.fields["power_level"]
    assert "stats.population" in rendered.fields
    assert "worshipped_son_id" in rendered.fields
    assert "Image prompt rules" in rendered.fields["image_prompt"]


def test_birth_world_lists_stars() -> None:
    text = tool_description(SonToolId.BIRTH_WORLD, RULES, ToolTextContext(stars=[StarLine(id=4, name="Ka", type_label="Red giant")]))
    assert "star_id 4: Ka (Red giant)" in text
    assert tool_description(SonToolId.BIRTH_WORLD, RULES).endswith("none")


def test_unknown_tool_is_rejected() -> None:
    with pytest.raises(UnknownToolError):
        tool_text(cast(SonToolId, "no_such_tool"), RULES)
