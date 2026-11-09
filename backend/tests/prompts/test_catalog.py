import re
from pathlib import Path

import pytest
from jinja2 import UndefinedError

from aerona.domain.enums.world import LoreLanguage
from aerona.prompts import PROMPTS, PromptId, render
from aerona.prompts.contexts.base import EmptyContext, LoreContext
from aerona.prompts.contexts.blocks import WorldSummaryContext
from aerona.prompts.contexts.son_turn import SonTurnUserContext
from aerona.prompts.environment import TEMPLATE_ROOT, TEMPLATE_SUFFIX, environment
from aerona.prompts.errors import PromptContextMismatchError
from tests.prompts.samples import SAMPLES, sample_context

LEAKS = re.compile(r"\{\{|\{%|\bNone\b|\bTrue\b|\bFalse\b|<.*? object at ")
LORE_DIRECTIVE = "in Turkish"
LORE_CONTEXT_FIELD = "lore_language"


def test_every_prompt_id_is_registered() -> None:
    assert set(PROMPTS) == set(PromptId)


def test_every_prompt_has_a_sample() -> None:
    assert set(SAMPLES) == set(PromptId)


@pytest.mark.parametrize("prompt_id", list(PromptId))
def test_every_prompt_has_a_template(prompt_id: PromptId) -> None:
    path = TEMPLATE_ROOT / PROMPTS[prompt_id].template_path
    assert path.is_file()
    assert path.name == f"{prompt_id}{TEMPLATE_SUFFIX}"


@pytest.mark.parametrize("prompt_id", list(PromptId))
def test_every_prompt_renders_its_sample(prompt_id: PromptId) -> None:
    context = sample_context(prompt_id)
    assert type(context) is PROMPTS[prompt_id].context
    text = render(prompt_id, context)
    assert text.strip()
    assert not LEAKS.search(text), LEAKS.search(text)
    assert text == text.strip()


@pytest.mark.parametrize("prompt_id", [prompt for prompt, spec in PROMPTS.items() if issubclass(spec.context, LoreContext)])
def test_lore_prompts_carry_their_language(prompt_id: PromptId) -> None:
    context = sample_context(prompt_id)
    assert getattr(context, LORE_CONTEXT_FIELD) is LoreLanguage.TURKISH
    english = context.model_copy(update={LORE_CONTEXT_FIELD: LoreLanguage.ENGLISH})
    if prompt_id.value.endswith("system") or prompt_id is PromptId.LORE_LANGUAGE:
        assert LORE_DIRECTIVE in render(prompt_id, context)
        assert "in English" in render(prompt_id, english)


def test_every_lore_call_sends_a_language_directive() -> None:
    lore_contexts = {spec.context for spec in PROMPTS.values() if issubclass(spec.context, LoreContext)}
    for context in lore_contexts:
        prompts = [prompt for prompt, spec in PROMPTS.items() if spec.context is context]
        rendered = [render(prompt, sample_context(prompt)) for prompt in prompts]
        assert any(LORE_DIRECTIVE in text for text in rendered), context.__name__


def test_render_rejects_a_foreign_context() -> None:
    with pytest.raises(PromptContextMismatchError):
        render(PromptId.WORLD_HEADER, EmptyContext())


def test_strict_undefined_catches_missing_variables() -> None:
    template = environment().get_template(PROMPTS[PromptId.WORLD_LINE].template_path)
    with pytest.raises(UndefinedError):
        template.render()


def test_templates_have_no_jinja_comments_or_orphans() -> None:
    known = {PROMPTS[prompt].template_path for prompt in PromptId}
    for path in Path(TEMPLATE_ROOT).rglob(f"*{TEMPLATE_SUFFIX}"):
        text = path.read_text(encoding="utf-8")
        assert "{#" not in text, path
        relative = path.relative_to(TEMPLATE_ROOT).as_posix()
        assert relative in known or path.name.startswith("_") or path.parent.name in {"son", "mortal"} or relative == "shared/macros.md.j2", relative


def test_world_summary_single_section_and_empty_section() -> None:
    context = sample_context(PromptId.WORLD_SUMMARY)
    events = render(PromptId.WORLD_SUMMARY, context.model_copy(update={"section": "events"}))
    assert events.startswith("RECENT EVENTS:")
    assert "PANTHEON" not in events
    empty = render(PromptId.WORLD_SUMMARY, context.model_copy(update={"section": "legends", "legends": []}))
    assert empty == 'There is nothing to show in the "legends" section.'


def test_world_summary_respects_the_summary_budget() -> None:
    context = sample_context(PromptId.WORLD_SUMMARY)
    assert isinstance(context, WorldSummaryContext)
    rules = context.rules
    huge = "\n".join(f"- #{index} A very long geography line about salt and bone" for index in range(4000))
    text = render(PromptId.WORLD_SUMMARY, context.model_copy(update={"geography": huge}))
    assert len(text) <= rules.context.son_summary_chars + 200
    assert "more lines" in text


def test_world_header_hides_mood_and_doom_when_short_or_calm() -> None:
    context = sample_context(PromptId.WORLD_HEADER)
    short = render(PromptId.WORLD_HEADER, context.model_copy(update={"short": True, "doom": 1}))
    assert "MOOD" not in short
    assert "DOOM CLOCK" not in short
    assert "PROHIBITIONS" in short
    full = render(PromptId.WORLD_HEADER, context)
    assert "about to overflow" in full
    assert "30% cheaper" in full


def test_son_turn_user_respects_the_prompt_budget() -> None:
    context = sample_context(PromptId.SON_TURN_USER)
    assert isinstance(context, SonTurnUserContext)
    limit = context.rules.context.son_prompt_chars
    text = render(PromptId.SON_TURN_USER, context.model_copy(update={"world_summary": "x\n" * limit}))
    assert len(text) <= limit + 200
    assert text.endswith("from the list above.")


def test_age_events_by_world_shares_the_budget_fairly() -> None:
    context = sample_context(PromptId.AGE_EVENTS_BY_WORLD)
    text = render(PromptId.AGE_EVENTS_BY_WORLD, context)
    assert "— Aerona (world#1) —" in text
    assert "— Cosmos and sky —" in text
    assert "(this age 3 times)" in text
