import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from aerona.db.columns import column_bounds
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import MortalStats, PeopleStats
from aerona.engine.primitives.stats import move_stat, stat
from aerona.engine.primitives.transfers import move_amount

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

PAIRED = """
def by_hand(payer, payee, rules):
    shift_stat(payer, "wealth", -rules.price)
    shift_stat(payee, "wealth", rules.price)


def floored(payer, payee, price):
    shift_stat(payer, "wealth", -price // 10)
    shift_stat(payee, "wealth", price // 10)


def one_sided(payer, rules):
    shift_stat(payer, "wealth", -rules.price)


def moved(payer, payee, rules):
    move_stat(payer, payee, "wealth", rules.price)
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_transfers", REPOSITORY_ROOT / "scripts" / "check_transfers.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_transfers"] = module
    spec.loader.exec_module(module)
    return module


def test_a_stat_moved_by_two_hand_written_shifts_is_flagged(tmp_path: Path) -> None:
    source = tmp_path / "module.py"
    source.write_text(PAIRED)
    found = checker().scan(source)
    assert [(item.function, item.column, item.payer, item.payee) for item in found] == [
        ("by_hand", "wealth", "payer", "payee"),
        ("floored", "wealth", "payer", "payee"),
    ]


def people(name: str, wealth: int) -> EntityRow:
    return EntityRow(id=hash(name) % 1000, name=name, entity_type=EntityType.PEOPLE, stats=PeopleStats(population=100, wealth=wealth))


def test_moving_a_stat_never_creates_or_destroys_it() -> None:
    poor, rich, full = people("Poor", 3), people("Rich", 90), people("Full", 98)
    assert move_stat(poor, rich, "wealth", 10) == 3 and stat(poor, "wealth") == 0 and stat(rich, "wealth") == 93
    assert move_stat(rich, full, "wealth", 10) == 2 and stat(rich, "wealth") == 91 and stat(full, "wealth") == 100
    lone = EntityRow(id=5, name="Lone", entity_type=EntityType.MORTAL, stats=MortalStats(hp=50))
    assert move_stat(lone, rich, "wealth", 10) == 0 and stat(rich, "wealth") == 91
    assert move_stat(rich, lone, "wealth", 10) == 0 and stat(rich, "wealth") == 91
    assert move_stat(rich, poor, "wealth", 0) == 0


def test_the_engine_moves_every_paired_amount_through_a_helper() -> None:
    module = checker()
    assert [finding for path in sorted(module.SOURCE.rglob("*.py")) for finding in module.scan(path)] == []


def test_moving_an_amount_never_pushes_either_side_past_its_bounds() -> None:
    payer = MortalProfileRow(entity_id=1, wealth=50, locked=[])
    full = MortalProfileRow(entity_id=2, wealth=95, locked=[])
    assert not move_amount(payer, full, "wealth", 10)
    assert payer.wealth == 50 and full.wealth == 95
    poor = MortalProfileRow(entity_id=3, wealth=4, locked=[])
    assert not move_amount(poor, payer, "wealth", 10)
    assert poor.wealth == 4 and payer.wealth == 50
    assert move_amount(payer, full, "wealth", 5) and payer.wealth == 45 and full.wealth == 100
    assert column_bounds(PolityProfileRow.__table__)["debt"] == (0, None)
