import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PROMPT = REPOSITORY_ROOT / "backend/src/aerona/prompts/tools/sample.py"
TEMPLATE = REPOSITORY_ROOT / "backend/src/aerona/prompts/templates/sample.md.j2"


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_prompt_bias", REPOSITORY_ROOT / "scripts" / "check_prompt_bias.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_prompt_bias"] = module
    spec.loader.exec_module(module)
    return module


def rules_hit(module: ModuleType, path: Path, text: str) -> set[str]:
    return {finding.rule for finding in module.matches(path, 1, text, True)}


def test_borrowed_textile_imagery_in_model_text_is_caught() -> None:
    module = checker()
    for text in (
        "You have woven enough bonds this age.",
        "It densifies the world's web.",
        "the threads of fate have not let go of them yet",
        "A storm severed the route; its stitch closes soon.",
        "worlds are strung like beads on a thread",
        "OPEN STORIES (threads Fate is tracking)",
    ):
        assert "borrowed imagery" in rules_hit(module, PROMPT, text), text
    assert "borrowed imagery" not in rules_hit(module, PROMPT, "weave_chimera")
    assert "borrowed imagery" not in rules_hit(module, TEMPLATE, "{% for thread in threads %}{{ thread.id }}{% endfor %}")
    assert "borrowed imagery" not in rules_hit(module, PROMPT, "You declare a bond between two existing things.")


def test_a_steering_example_list_is_caught_without_a_lead_in() -> None:
    module = checker()
    assert "steering example" in rules_hit(module, PROMPT, "ore vein, healing herb, sacred spring, bone bed…")
    assert "steering example" in rules_hit(module, PROMPT, "light-sail, bone-hulled, generation ship…")
    assert "steering example" not in rules_hit(module, PROMPT, "ore vein, healing herb, sacred spring, clay pit…")


def test_no_model_facing_text_carries_bias() -> None:
    assert checker().scan() == []


def test_example_names_and_lists_in_placeholders_are_caught() -> None:
    module = checker()
    form = REPOSITORY_ROOT / "frontend/src/features/sample.tsx"
    assert "example placeholder" in rules_hit(module, form, "placeholder='Ashwing, Glimmerdeer…'")
    assert "example placeholder" in rules_hit(module, form, "placeholder='Vharrun the Ash-Maw…'")
    assert "example placeholder" in rules_hit(module, form, "placeholder='Any tone you like: hopeful, epic, grim…'")
    assert "example placeholder" not in rules_hit(module, form, "placeholder='Choose a realm, cult or people…'")
    assert "example placeholder" not in rules_hit(module, form, "placeholder='Describe what you reveal: a being, a place, an event…'")
    assert "example placeholder" not in rules_hit(module, form, "placeholder='Choose the patron…'")


def test_gendered_fellowships_are_caught_in_prose_and_in_named_values() -> None:
    module = checker()
    for text in (
        "Companions in arms swear blood brotherhood.",
        "You swear an oath (fealty, blood_brotherhood).",
        "the Warrior Brotherhood rises",
        "a fraternal order",
        "the sisterhood of the well",
    ):
        assert "gendered default" in rules_hit(module, PROMPT, text), text
    assert "gendered default" not in rules_hit(module, PROMPT, "Companions in arms swear sworn kinship.")
