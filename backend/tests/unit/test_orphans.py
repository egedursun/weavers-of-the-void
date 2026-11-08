import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

SOURCE = """
SPARE = 3
USED = 4


def lonely() -> int:
    return USED


def wanted() -> int:
    return USED


@router.get("/x")
def routed() -> int:
    return wanted()
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_orphans", REPOSITORY_ROOT / "scripts" / "check_orphans.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_orphans"] = module
    spec.loader.exec_module(module)
    return module


def test_functions_and_constants_nothing_uses_are_found() -> None:
    module = checker()
    found = module.orphans({Path("module.py"): SOURCE}, "")
    assert sorted(item.name for item in found) == ["SPARE", "lonely"]
    assert [item.name for item in module.orphans({Path("module.py"): SOURCE}, "lonely() SPARE")] == []


def test_every_function_and_constant_of_the_backend_is_used() -> None:
    module = checker()
    users = "\n".join(path.read_text(encoding="utf-8") for folder in module.USERS for path in sorted(folder.rglob("*.py")) if path.name != "check_orphans.py")
    assert module.orphans(module.sources(), users) == []
