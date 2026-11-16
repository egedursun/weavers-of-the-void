import re
from pathlib import Path

from aerona.engine.primitives.numbers import apportion

ENGINE = Path(__file__).resolve().parents[2] / "src" / "aerona"


def test_a_split_gives_every_unit_and_none_to_what_has_no_weight() -> None:
    parts = apportion(7, {"farmer": 64.0, "artisan": 12.5, "monastic": 0.0, "unemployed": 0.0})
    assert sum(parts.values()) == 7
    assert parts.get("unemployed", 0) == 0 and parts.get("monastic", 0) == 0
    assert apportion(5, {"a": 0.0}) == {} and apportion(0, {"a": 1.0}) == {}
    assert apportion(10, {"a": 1.0, "b": 1.0, "c": 1.0}) == apportion(10, {"a": 1.0, "b": 1.0, "c": 1.0})


def test_no_split_hands_its_remainder_to_whatever_comes_last() -> None:
    found = [
        f"{path.relative_to(ENGINE)}:{number}"
        for path in sorted(ENGINE.rglob("*.py"))
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if re.search(r"if \w+ == len\(\w+\) - 1 else", line)
    ]
    assert found == [], "split an amount with apportion, so a remainder never lands on a share of nothing"
