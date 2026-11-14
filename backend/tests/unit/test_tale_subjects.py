import re
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"
TALE_TABLES = re.compile(r"\b(ArcRow|ArcFigureRow|SetupRow|AgeEchoRow)\b")
ENTITY_ONLY = re.compile(r"get\(EntityRow, \w+\.(subject_node_id|node_id|source_node_id|echo_node_id)\b")


def test_tales_name_their_subjects_whatever_kind_of_node_they_are() -> None:
    found = [
        f"{path.relative_to(SOURCE)}:{number}"
        for path in sorted(SOURCE.rglob("*.py"))
        if TALE_TABLES.search(text := path.read_text())
        for number, line in enumerate(text.splitlines(), 1)
        if ENTITY_ONLY.search(line)
    ]
    assert found == [], f"a tale's subject, figure or echo may be a god or any node: name it through NodeRepository.name_of: {found}"
