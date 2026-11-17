import importlib.util
import sys
from enum import StrEnum
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class Colour(StrEnum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


TABLE = {Colour.RED: 1, Colour.GREEN: 2}
WARM = frozenset({Colour.RED})
NAMESPACE = {"TABLE": TABLE, "WARM": WARM, "Colour": Colour}

UNGUARDED = """
def weight(colour):
    return TABLE[colour]
"""

GUARDED = """
def weight(colour):
    if colour in TABLE:
        return TABLE[colour]
    return 0


def other(colour):
    if colour is Colour.BLUE:
        return 0
    return TABLE[colour]


def constant():
    return TABLE[Colour.RED]


def looped():
    return [TABLE[colour] for colour in WARM]


def chained(colour):
    return colour in TABLE and TABLE[colour] > 1


async def queried(session):
    for row in await session.scalars(select(Row).where(Row.colour.in_(list(TABLE)))):
        TABLE[row.colour]
"""

PROVEN = """
def weight(colour):
    return TABLE[colour]
"""


def script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_partial_reads", REPOSITORY_ROOT / "scripts" / "check_partial_reads.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_partial_reads"] = module
    spec.loader.exec_module(module)
    return module


def reads(tmp_path: Path, name: str, text: str, proven: dict[tuple[str, str, str], str] | None = None) -> tuple[list[str], set[tuple[str, str, str]]]:
    check = script()
    source = tmp_path / name
    source.write_text(text, encoding="utf-8")
    used: set[tuple[str, str, str]] = set()
    found = check.reads_in(source, check.partial_tables(NAMESPACE), NAMESPACE, proven or {}, used)
    return [f"{read.table}[{read.key}]" for read in found], used


def test_an_unguarded_read_of_a_partial_table_is_found(tmp_path: Path) -> None:
    assert reads(tmp_path, "unguarded.py", UNGUARDED)[0] == ["TABLE[colour]"]


def test_reads_proven_by_membership_exits_constants_loops_and_queries_pass(tmp_path: Path) -> None:
    assert reads(tmp_path, "guarded.py", GUARDED)[0] == []


def test_a_proven_read_is_marked_used(tmp_path: Path) -> None:
    proven = {("proven.py", "TABLE", "colour"): "the only caller passes a colour of the table"}
    found, used = reads(tmp_path, "proven.py", PROVEN, proven)
    assert found == [] and used == set(proven)


def test_a_total_table_is_not_partial() -> None:
    check = script()
    assert check.partial_tables({"FULL": {member: 1 for member in Colour}}) == {}
