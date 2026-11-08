import importlib
import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
STANDALONE = ("aerona.engine.ecology.control", "aerona.engine.lore.control", "aerona.engine.lore.rites", "aerona.engine.ecology.flora_control")


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_import_cycles", REPOSITORY_ROOT / "scripts" / "check_import_cycles.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_import_cycles"] = module
    spec.loader.exec_module(module)
    return module


def test_a_cycle_of_module_imports_is_found() -> None:
    module = checker()
    graph = {"a": {"b"}, "b": {"c"}, "c": {"a"}, "d": {"a"}}
    assert module.cycles(graph) == [["a", "b", "c"]]
    assert module.cycles({"a": {"b"}, "b": set()}) == []


def test_no_module_of_the_package_imports_itself_in_a_circle() -> None:
    module = checker()
    assert module.cycles(module.import_graph(module.module_names())) == []


def test_the_control_modules_import_on_their_own() -> None:
    for name in STANDALONE:
        done = subprocess.run([sys.executable, "-c", f"import {name}"], capture_output=True, text=True, check=False)
        assert done.returncode == 0, done.stderr[-400:]
