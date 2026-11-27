import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from aerona.core.grammar import spoken
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.world_view import BindingNeed

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_enum_caches", REPOSITORY_ROOT / "scripts" / "check_enum_caches.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_enum_caches"] = module
    spec.loader.exec_module(module)
    return module


def test_a_word_for_one_enum_never_answers_for_another_with_the_same_name() -> None:
    assert spoken(BindingNeed.PLACE) == "a place of its own"
    assert spoken(IncidentRole.PLACE) == "place"
    assert spoken(BindingNeed.PLACE) == "a place of its own"


def test_a_cache_keyed_by_an_enum_of_any_type_is_caught() -> None:
    open_key = "from enum import Enum\nfrom functools import cache\n\n@cache\ndef worded(member: Enum) -> str:\n    return str(member.value)\n"
    typed_key = "from enum import Enum\nfrom functools import cache\n\n@cache\ndef worded(kind: type[Enum], value: str) -> str:\n    return value\n"
    assert checker().enum_caches(Path("a.py"), open_key) and not checker().enum_caches(Path("b.py"), typed_key)


def test_no_cache_is_keyed_by_an_enum_of_any_type() -> None:
    module = checker()
    assert [f"{item.path.name}:{item.function}" for path, text in module.sources().items() for item in module.enum_caches(path, text)] == []
