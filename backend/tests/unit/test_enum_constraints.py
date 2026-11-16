import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from aerona.domain.enums.travel import RouteClosure

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_enum_constraints", REPOSITORY_ROOT / "scripts" / "check_enum_constraints.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_enum_constraints"] = module
    spec.loader.exec_module(module)
    return module


def test_a_check_constraint_reads_back_as_its_values() -> None:
    sql = "CREATE TABLE routes (closure VARCHAR(40), CONSTRAINT ck_routes_closure CHECK (closure IN ('sealed', 'severed')))"
    assert checker().constraint_values(sql, "closure") == {"sealed", "severed"}


def test_a_value_the_migrations_never_added_is_found() -> None:
    stored = {value.value for value in RouteClosure} - {RouteClosure.WORN.value}
    sql = (
        "CREATE TABLE routes (closure VARCHAR(40), CONSTRAINT ck_routes_closure CHECK (closure IN ("
        + ", ".join(f"'{value}'" for value in sorted(stored))
        + ")))"
    )
    assert checker().constraint_values(sql, "closure") != {value.value for value in RouteClosure}


def test_every_enum_column_of_the_migrated_schema_matches_its_enum() -> None:
    assert checker().findings() == []
