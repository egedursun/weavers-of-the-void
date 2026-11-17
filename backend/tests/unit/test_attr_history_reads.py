import re
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"
SLOW_HISTORY = re.compile(r"\.attrs\b[^\n]*\.history\b|attribute\.history\b|\.attrs\[[^\]]+\]\.history\b")


def slow_history_reads(text: str) -> list[int]:
    return [text.count("\n", 0, match.start()) + 1 for match in SLOW_HISTORY.finditer(text)]


def test_a_history_read_through_the_attribute_map_is_found() -> None:
    assert slow_history_reads("changed = state.attrs['value'].history.has_changes()") == [1]
    assert slow_history_reads("changed = {a.key for a in state.attrs if attribute.history.has_changes()}") == [1]
    assert slow_history_reads("changed = history_of(state, 'value').has_changes()") == []


def test_no_source_reads_a_change_history_through_the_attribute_map() -> None:
    found = [f"{path.relative_to(SOURCE)}:{line}" for path in sorted(SOURCE.rglob("*.py")) for line in slow_history_reads(path.read_text(encoding="utf-8"))]
    assert found == []
