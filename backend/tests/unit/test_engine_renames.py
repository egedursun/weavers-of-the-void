import re
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2] / "src" / "aerona" / "engine"
DIRECT = re.compile(r"^\s*(?:\w+\.)*(?:entity|faction|realm|polity|settlement|town|company|league)\.name\s*=", re.MULTILINE)
LEVERS = "control"


def test_the_engine_renames_a_record_everywhere_never_by_its_name_field_alone() -> None:
    found = [
        f"{path.relative_to(ENGINE)}:{text[: match.start()].count(chr(10)) + 1}"
        for path in sorted(ENGINE.rglob("*.py"))
        if LEVERS not in path.stem and path.name != "renames.py"
        for text in [path.read_text(encoding="utf-8")]
        for match in DIRECT.finditer(text)
    ]
    assert found == []
