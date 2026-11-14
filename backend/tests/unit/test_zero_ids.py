import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_zero_ids", REPOSITORY_ROOT / "scripts" / "check_zero_ids.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_zero_ids"] = module
    spec.loader.exec_module(module)
    return module


def test_a_hook_asked_for_record_zero_is_caught() -> None:
    screen = (
        "const seams = useSeamNames(ground?.world_id ?? 0)\n"
        "const [stress, setStress] = useState(held?.stress ?? 0)\n"
        "const realm = useAfterlife(soul.spirit?.id ?? null)\n"
    )
    assert [(item.line, item.text) for item in checker().zero_ids({Path("Panel.tsx"): screen})] == [(1, "useSeamNames(ground?.world_id ?? 0)")]


def test_no_screen_asks_a_hook_for_record_zero() -> None:
    module = checker()
    assert module.zero_ids(module.screens()) == []
