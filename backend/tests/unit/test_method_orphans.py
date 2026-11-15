import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

SOURCE = """
class EconomyWorld:
    def ore_yield(self, rules, world_id):
        return 1.0

    def harvest(self):
        return self.ore_share()

    def ore_share(self):
        return 2.0


class Column(TypeDecorator[int]):
    def coerce_compared_value(self, op, value):
        return self
"""
READER = """
world.harvest()
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_method_orphans", REPOSITORY_ROOT / "scripts" / "check_method_orphans.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_method_orphans"] = module
    spec.loader.exec_module(module)
    return module


def test_a_method_nothing_calls_is_flagged_and_framework_hooks_are_not() -> None:
    found = checker().unused_methods({Path("module.py"): SOURCE}, {Path("module.py"): SOURCE, Path("reader.py"): READER})
    assert [item.name for item in found] == ["EconomyWorld.ore_yield"]


def test_the_backend_calls_every_method_it_defines() -> None:
    module = checker()
    sources = {path: path.read_text(encoding="utf-8") for path in sorted(module.SOURCE.rglob("*.py")) if module.readable(path)}
    readers = {path: path.read_text(encoding="utf-8") for path in sorted(module.BACKEND.rglob("*")) if path.is_file() and module.readable(path)}
    assert module.unused_methods(sources, readers) == []
