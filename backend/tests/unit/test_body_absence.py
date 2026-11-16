import re
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2] / "src" / "aerona" / "engine"
ABSENCE_IS_LACK = {"lifecycle/wounds.py": "BodyFunction.VENOM"}


def test_a_thing_with_no_body_record_is_never_read_as_maimed() -> None:
    found: list[str] = []
    for path in sorted(ENGINE.rglob("*.py")):
        relative = path.relative_to(ENGINE).as_posix()
        if relative == "body/book.py":
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if re.search(r"\bfunction_level\(", line) and ABSENCE_IS_LACK.get(relative, "\0") not in line:
                found.append(f"{relative}: {line.strip()}")
    assert found == [], "read a body through function_unhindered, so a thing with no body record keeps every function"
