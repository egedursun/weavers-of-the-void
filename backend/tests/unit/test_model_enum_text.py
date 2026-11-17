import importlib.util
from pathlib import Path
from types import ModuleType

from aerona.core.grammar import spoken
from aerona.domain.enums.creator import CreatorSignKind

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def guard() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_model_enum_text", REPOSITORY_ROOT / "scripts" / "check_model_enum_text.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_raw_enum_key_in_model_text_is_found_and_a_spoken_one_passes() -> None:
    checker = guard()
    assert checker.raw_values('f"your town grew {profile.morphology.value}; the sign {row.kind.value}"') == [(1, "profile.morphology"), (1, "row.kind")]
    assert checker.raw_values('f"your town grew {spoken(profile.morphology)}"') == []
    assert checker.raw_values('f"tools.mortal.demand_{args.demand.value}"') == []
    assert checker.raw_values('f"{fact.key}: {fact.value!s}"') == []
    assert spoken(CreatorSignKind.COVENANT_OFFER) == "covenant offer"
