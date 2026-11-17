import re
from pathlib import Path

from aerona.domain.enums.loops import BalanceLoop
from aerona.rules.registry.loops import LoopRules

ROOT = Path(__file__).resolve().parents[3]
ENGINE = ROOT / "backend" / "src" / "aerona" / "engine"
SPEC = ROOT / "docs" / "spec" / "13-depth-expansion.md"


KINDS_SPEC = ROOT / "docs" / "spec" / "16-minds-powers-living-craft.md"
KIND_LOOPS = {"L109": BalanceLoop.KIND_PRESTIGE, "L110": BalanceLoop.KIND_SUBSTITUTION}


def test_every_balancing_loop_of_the_spec_has_a_delay_rule() -> None:
    balancing = re.findall(r"^\| (L\d+) \| B \|", SPEC.read_text(encoding="utf-8"), flags=re.MULTILINE)
    assert len(set(balancing)) == len(BalanceLoop) - len(KIND_LOOPS)
    assert {f"delay_{loop.value}" for loop in BalanceLoop} == set(LoopRules.__dataclass_fields__)


def test_the_loops_of_the_ways_of_life_carry_their_delays() -> None:
    text = KINDS_SPEC.read_text(encoding="utf-8")
    assert all(re.search(rf"\b{loop} \((?:R|B)\)", text) for loop in KIND_LOOPS)
    assert all(f"delay_{loop.value}" in LoopRules.__dataclass_fields__ for loop in KIND_LOOPS.values())


def test_every_loop_delay_is_read_by_the_engine() -> None:
    read = {match for path in ENGINE.rglob("*.py") for match in re.findall(r"lagged\(\s*ctx,\s*BalanceLoop\.([A-Z_]+)", path.read_text(encoding="utf-8"))}
    assert sorted(loop.name for loop in BalanceLoop if loop.name not in read) == []
