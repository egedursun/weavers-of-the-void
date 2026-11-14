import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_record_cuts", REPOSITORY_ROOT / "scripts" / "check_record_cuts.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_record_cuts"] = module
    spec.loader.exec_module(module)
    return module


def test_a_reader_that_drops_folded_lines_is_caught() -> None:
    reader = (
        "statement = select(ChronicleRow).where(ChronicleRow.kind != ChronicleKind.ENGINE_RAW)\n"
        "rows = select(ChronicleRow).where(ChronicleRow.visible.is_(True))\n"
        "rows = select(ChronicleRow).where(ChronicleRow.kind.not_in([ChronicleKind.ENGINE_RAW, ChronicleKind.SYSTEM]))\n"
        "rows = select(ChronicleRow).where(kept_lines())\n"
    )
    assert [item.line for item in checker().cuts({Path("model.py"): reader})] == [1, 2, 3]


def test_no_reader_of_the_chronicle_drops_folded_lines() -> None:
    module = checker()
    assert module.cuts(module.readers()) == []


def test_a_writer_that_cuts_what_it_stores_at_a_fixed_length_is_caught() -> None:
    writer = (
        "row.note = label[:120]\n"
        "row.summary = phase.summary\n"
        "first = name[:1].upper()\n"
        "casting.effect = text[:480] or 'nothing'\n"
    )
    assert [item.line for item in checker().fixed_cuts({Path("writer.py"): writer})] == [1, 4]


def test_no_writer_cuts_what_it_stores() -> None:
    module = checker()
    assert module.fixed_cuts(module.writers()) == []
