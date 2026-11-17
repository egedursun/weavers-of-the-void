import re
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"
PARITY_PICK = re.compile(r"""%\s*2(?:\s*==\s*[01])?\s+else\s+["']""")


def parity_picks(text: str) -> list[int]:
    return [text.count("\n", 0, match.start()) + 1 for match in PARITY_PICK.finditer(text)]


def test_a_look_picked_by_the_parity_of_an_id_is_found() -> None:
    assert parity_picks('field = "or" if house.id % 2 else "sable"') == [1]
    assert parity_picks("field = pick(list(Tincture))") == []


def test_no_engine_or_service_code_picks_a_look_by_the_parity_of_an_id() -> None:
    found = [f"{path.relative_to(SOURCE)}:{line}" for path in sorted(SOURCE.rglob("*.py")) for line in parity_picks(path.read_text(encoding="utf-8"))]
    assert found == []
