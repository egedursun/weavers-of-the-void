from dataclasses import replace

from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.foreign_god import ForeignGodPowerEffect
from aerona.domain.enums.son import Stat
from aerona.domain.enums.travel import VehicleKind
from aerona.prompts.catalog import render
from aerona.prompts.contexts import opportunities as o
from aerona.prompts.contexts.common import NamedRecord
from aerona.prompts.data.deepening import SPECIAL_SECTIONS, special_section
from aerona.prompts.data.foreign_gods import foreign_power_effect, foreign_stat_effect
from aerona.prompts.data.images import MEGAFAUNA_DIRECTION, OUTER_BEING_TAIL, SCALE_TAIL, ImageSubjectTraits, fix_image_prompt, image_direction
from aerona.prompts.ids import PromptId
from aerona.rules.registry import Rules

RULES = Rules()


def test_image_direction_by_kind() -> None:
    assert image_direction(ImageSubjectTraits(EntityType.VESSEL, False, VehicleKind.GATE)).startswith("a gate between worlds")
    assert image_direction(ImageSubjectTraits(EntityType.VESSEL, False, VehicleKind.SHIP)).startswith("a vessel between worlds")
    assert image_direction(ImageSubjectTraits(EntityType.SPECIES, True)) == MEGAFAUNA_DIRECTION
    assert image_direction(ImageSubjectTraits(EntityType.ARMY, False)).startswith("the army")


def test_fix_image_prompt_adds_tails_and_respects_length() -> None:
    fixed = fix_image_prompt("a thing in the dark " * 100, EntityType.OUTER_BEING, False, 300)
    assert fixed.endswith(OUTER_BEING_TAIL)
    assert len(fixed) <= 300
    assert fix_image_prompt("a colossal beast", EntityType.SPECIES, True, 300) == "a colossal beast"
    assert fix_image_prompt("a beast.", EntityType.SPECIES, True, 300).endswith(SCALE_TAIL)


def test_special_sections() -> None:
    assert special_section(EntityType.PEOPLE) is SPECIAL_SECTIONS[EntityType.PEOPLE]
    assert special_section(EntityType.REGION) is None


def test_stale_threads_lead_and_tension_rises_only_when_the_rule_asks() -> None:
    lines: list[o.SonOpportunity] = [
        o.OpenThreads(thread_ids=[1]),
        o.StaleThreads(threads=[o.StaleThread(id=1, text="old")]),
        o.RebelSiblings(siblings=[NamedRecord(id=3, name="Tesh")]),
    ]
    plain = o.SonOpportunitiesContext(rules=RULES, lines=lines).ordered
    assert [type(line) for line in plain] == [o.StaleThreads, o.OpenThreads, o.RebelSiblings]
    tense = replace(RULES, opportunities=replace(RULES.opportunities, tension_first=1))
    raised = o.SonOpportunitiesContext(rules=tense, lines=lines).ordered
    assert [type(line) for line in raised] == [o.RebelSiblings, o.StaleThreads, o.OpenThreads]


def test_lines_without_available_tools_are_dropped() -> None:
    lines: list[o.SonOpportunity] = [
        o.RivalMortals(mortals=[o.TargetMortal(id=1, name="Arro", patron="Tesh", cost=40, chance=50)]),
        o.Unclaimed(communities=[NamedRecord(id=2, name="Vor")]),
    ]
    text = render(PromptId.SON_OPPORTUNITIES, o.SonOpportunitiesContext(rules=RULES, lines=lines, available_tools=["miracle"]))
    assert "take_life" not in text
    assert "win them with miracle" in text
    assert "send_dream" not in text
    assert text.count("\n") == 0


def test_foreign_god_texts_follow_live_rules() -> None:
    changed = replace(RULES, foreign_gods=replace(RULES.foreign_gods, power_shield=99, talk_will=250))
    assert "+99" in foreign_power_effect(ForeignGodPowerEffect.SHIELD, changed)
    assert "gives 2.5" in foreign_stat_effect(Stat.WILL, changed)
    for stat in Stat:
        assert "{{" not in foreign_stat_effect(stat, RULES)
    for effect in ForeignGodPowerEffect:
        assert foreign_power_effect(effect, RULES)
