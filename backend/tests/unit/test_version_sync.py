import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("version_script", REPOSITORY_ROOT / "scripts" / "version.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["version_script"] = module
    spec.loader.exec_module(module)
    return module


def test_every_copy_of_the_version_matches_the_version_file() -> None:
    version = script()
    assert version.parsed(version.canonical_version()) is not None
    assert set(version.declared_versions().values()) == {version.canonical_version()}


@pytest.mark.parametrize(
    ("start", "part", "pre", "expected"),
    [
        ("0.1.0", "patch", "", "0.1.1"),
        ("0.1.3", "minor", "", "0.2.0"),
        ("0.9.2-beta.1", "major", "", "1.0.0"),
        ("0.1.0", "minor", "beta.1", "0.2.0-beta.1"),
    ],
)
def test_a_bump_moves_the_right_part_and_clears_the_lower_ones(start: str, part: str, pre: str, expected: str) -> None:
    version = script()
    current = version.parsed(start)
    assert current is not None
    assert str(version.bumped(current, part, pre)) == expected


def test_only_real_versions_are_accepted() -> None:
    version = script()
    assert version.parsed("0.1.0-beta") is not None
    assert version.parsed("1.2") is None
    assert version.parsed("01.2.3") is None
    assert version.parsed("v0.1.0") is None


def test_a_mention_is_rewritten_in_place_and_read_back(tmp_path: Path) -> None:
    version = script()
    readme = tmp_path / "README.md"
    readme.write_text('<img alt="Version" src="https://img.shields.io/badge/version-0.1.0-d4af37?style=flat-square">\n', encoding="utf-8")
    badge = version.Mention(readme, version.MENTIONS[0].pattern, escaped=True)
    badge.write("0.2.0-beta.1")
    assert "badge/version-0.2.0--beta.1-d4af37?style" in readme.read_text(encoding="utf-8")
    assert badge.read() == "0.2.0-beta.1"
    notes = tmp_path / "notes.md"
    notes.write_text("  * Sürüm 0.1.0, çekirdek ürünü.\n", encoding="utf-8")
    told = version.Mention(notes, version.MENTIONS[1].pattern)
    told.write("1.0.0")
    assert re.search(r"Sürüm 1\.0\.0, ", notes.read_text(encoding="utf-8"))
    assert told.read() == "1.0.0"
