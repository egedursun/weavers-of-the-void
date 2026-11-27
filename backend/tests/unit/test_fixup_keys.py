import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RAW_LOOKUPS = """
async def backfill(session):
    if await session.get(AppliedFixupRow, KEY) is not None:
        return 0
    done = set(await session.scalars(select(AppliedFixupRow.key)))
    session.add(AppliedFixupRow(key="universe.born_current", result={}))
"""
ROUTED = """
async def backfill(session):
    if not await fixup_due(session, KEY):
        return 0
    session.add(AppliedFixupRow(key=KEY, result={}))
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_fixup_keys", REPOSITORY_ROOT / "scripts" / "check_fixup_keys.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_fixup_keys"] = module
    spec.loader.exec_module(module)
    return module


def test_a_raw_fixup_lookup_and_a_stray_born_marker_are_caught() -> None:
    found = checker().problems_in(Path("engine") / "made" / "backfill.py", RAW_LOOKUPS)
    assert [what for _line, what in found] == ["looks up a fixup key", "selects fixup keys", "writes the born marker"]


def test_a_lookup_through_the_helper_passes() -> None:
    assert checker().problems_in(Path("engine") / "made" / "backfill.py", ROUTED) == []


def test_the_source_routes_every_fixup_lookup_through_the_helper() -> None:
    result = subprocess.run([sys.executable, str(REPOSITORY_ROOT / "scripts" / "check_fixup_keys.py")], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout
