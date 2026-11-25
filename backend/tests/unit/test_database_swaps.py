import re
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"
LIVE_TARGET = r"(?:live_path|database_path|paths\.database)"
SWAPS = (re.compile(rf"\.replace\((?:self\.)?{LIVE_TARGET}\)"), re.compile(rf"os\.replace\([^,]+,\s*[\w.]*{LIVE_TARGET}\)"))
GUARDED = "replace_file("


def unguarded_swaps(root: Path) -> list[str]:
    found: list[str] = []
    for path in sorted(root.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        if GUARDED in source:
            continue
        for number, line in enumerate(source.splitlines(), 1):
            if any(pattern.search(line) for pattern in SWAPS):
                found.append(f"{path.relative_to(root)}:{number}")
    return found


def test_a_live_database_file_is_swapped_only_through_replace_file() -> None:
    assert unguarded_swaps(SOURCE) == []


def test_the_guard_finds_a_bare_swap(tmp_path: Path) -> None:
    (tmp_path / "bare.py").write_text("staged.replace(self.live_path)\n", encoding="utf-8")
    assert unguarded_swaps(tmp_path) == ["bare.py:1"]
