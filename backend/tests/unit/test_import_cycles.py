import importlib
import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
STANDALONE = (
    "aerona.engine.ecology.control",
    "aerona.engine.lore.control",
    "aerona.engine.lore.rites",
    "aerona.engine.ecology.flora_control",
    "aerona.db.profile_guard",
    "aerona.services.player.profiles",
)


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


def test_importing_a_module_runs_the_packages_it_belongs_to_but_not_its_own() -> None:
    module = checker()
    modules = dict.fromkeys(("p", "p.inner", "p.sub", "p.sub.leaf", "q"), Path())
    assert module.run_on_import("q", "p.sub.leaf", modules) == {"p.sub.leaf", "p", "p.sub"}
    assert module.run_on_import("p.sub.other", "p.sub.leaf", modules) == {"p.sub.leaf"}
    graph = {"q": module.run_on_import("q", "p.sub.leaf", modules), "p.sub": {"p.inner"}, "p.inner": {"q"}, "p": set(), "p.sub.leaf": set()}
    assert module.cycles(graph) == [["p.inner", "p.sub", "q"]]
