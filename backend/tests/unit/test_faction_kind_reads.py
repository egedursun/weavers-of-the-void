import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

MAPPING = """
KIND_OF_ENGINE = MappingProxyType({EngineKind.MERCHANT_GUILD: FactionKind.MERCHANT_GUILD, EngineKind.REBELS: FactionKind.REBELS})
"""

SOURCE = """
def banks(rows):
    return [row for row in rows if row.engine_kind is EngineKind.MERCHANT_GUILD]


def query():
    return select(EntityRow).where(EntityRow.engine_kind == EngineKind.MERCHANT_GUILD)


def several():
    return select(EntityRow).where(EntityRow.engine_kind.in_([EngineKind.REBELS]))


def outside(row):
    return row.engine_kind not in (EngineKind.REBELS, EngineKind.FLEET)


def creation():
    return EntityRow(engine_kind=EngineKind.REBELS)


def other(row):
    return row.engine_kind is EngineKind.FLEET
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_faction_kinds", REPOSITORY_ROOT / "scripts" / "check_faction_kinds.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_a_faction_kind_read_through_engine_kind_is_caught_and_creation_and_other_kinds_are_not() -> None:
    module = checker()
    kinds = module.faction_engine_kinds(MAPPING)
    assert kinds == frozenset({"MERCHANT_GUILD", "REBELS"})
    assert module.reads_in(SOURCE, kinds) == [(3, "MERCHANT_GUILD"), (7, "MERCHANT_GUILD"), (11, "REBELS"), (15, "REBELS")]


def test_the_source_reads_every_faction_kind_from_the_profile() -> None:
    module = checker()
    assert module.main() == 0
