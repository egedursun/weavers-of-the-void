import re
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"
TAGGED = re.compile(r"\((?:Epoch|epoch) \{")
TOLD_TO_THE_MODEL = SOURCE / "agents"
SHOWN_TO_THE_PLAYER = SOURCE / "services" / "exchange.py"


def test_no_name_or_told_line_carries_the_epoch_in_brackets() -> None:
    found = [
        f"{path.relative_to(SOURCE)}:{number}"
        for path in sorted(SOURCE.rglob("*.py"))
        if TOLD_TO_THE_MODEL not in path.parents and path != SHOWN_TO_THE_PLAYER
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if TAGGED.search(line)
    ]
    assert found == [], f"a name or a told line writes the epoch in brackets; name it plainly: {found}"
