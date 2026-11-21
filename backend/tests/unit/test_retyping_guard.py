import re
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"
RETYPING = re.compile(r"\.entity_type\s*=[^=]|setattr\(\w+,\s*\"entity_type\"|\.set\(\w+,\s*\"entity_type\"")
HELPER = SOURCE / "engine" / "transform" / "ledger.py"


def test_a_record_changes_its_kind_only_through_the_retyping_that_clears_what_belongs_to_the_old_kind() -> None:
    found = [
        f"{path.relative_to(SOURCE)}:{number}"
        for path in sorted(SOURCE.rglob("*.py"))
        if path != HELPER and "alembic" not in path.parts
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if RETYPING.search(line)
    ]
    assert found == []
