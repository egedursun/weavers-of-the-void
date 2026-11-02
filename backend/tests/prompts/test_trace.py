import re
from pathlib import Path

from aerona.prompts.ids import PromptId
from aerona.prompts.trace import SPEC_ALIASES, SPEC_PROMPTS

COVERAGE = Path(__file__).resolve().parents[3] / "docs" / "spec" / "coverage.md"
REFERENCE = re.compile(r"\(prompts? ([a-z_. ]+(?:, [a-z_.]+)*)\)")


def referenced_prompts() -> set[str]:
    found: set[str] = set()
    for match in REFERENCE.finditer(COVERAGE.read_text(encoding="utf-8")):
        found.update(name.strip() for name in match.group(1).split(","))
    return found


def test_every_coverage_prompt_reference_is_implemented() -> None:
    references = referenced_prompts()
    assert references
    for name in references:
        resolved = SPEC_ALIASES.get(name, name)
        assert resolved in SPEC_PROMPTS, name


def test_trace_points_at_known_prompts() -> None:
    for prompt_ids in SPEC_PROMPTS.values():
        assert prompt_ids
        assert all(isinstance(prompt_id, PromptId) for prompt_id in prompt_ids)
