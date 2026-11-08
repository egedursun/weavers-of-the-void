from typing import Any

from aerona.prompts.contexts.opportunities import ordered_lines
from aerona.rules.registry import Rules


class Line:
    def __init__(self, name: str, *, first: bool = False, tension: bool = False) -> None:
        self.name, self.first, self.tension = name, first, tension


def test_by_default_no_line_is_pushed_up_for_its_conflict() -> None:
    assert Rules().opportunities.tension_first == 0
    lines: list[Any] = [Line("trade"), Line("rival", tension=True), Line("urgent", first=True), Line("feast")]
    assert [line.name for line in ordered_lines(lines, Rules().opportunities.tension_first > 0)] == ["urgent", "trade", "rival", "feast"]


def test_a_god_may_still_put_conflict_first() -> None:
    lines: list[Any] = [Line("trade"), Line("rival", tension=True), Line("urgent", first=True)]
    assert [line.name for line in ordered_lines(lines, True)] == ["rival", "urgent", "trade"]
