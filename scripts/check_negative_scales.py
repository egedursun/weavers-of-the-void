import re
import sys
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
SCANNED = (SOURCE / "engine", SOURCE / "services", SOURCE / "agents", SOURCE / "tools", SOURCE / "api")
sys.path.insert(0, str(SOURCE.parent))

import sqlalchemy as sa

import aerona.db.tables
from aerona.db.base import Base

FLOOR = re.compile(r"^\s*\(?\s*(\w+)\s+BETWEEN\s+(-?\d+)\s+AND", re.IGNORECASE)
BELOW = re.compile(r"\.(\w+)\s*(<\s*0\b|<=?\s*-\d+)")


@dataclass(frozen=True)
class Below:
    path: Path
    line: int
    field: str


def floors() -> dict[str, int]:
    found: dict[str, list[int | None]] = defaultdict(list)
    for table in Base.metadata.sorted_tables:
        bounded: dict[str, int] = {}
        for constraint in table.constraints:
            if isinstance(constraint, sa.CheckConstraint) and (match := FLOOR.match(str(constraint.sqltext))):
                bounded[match.group(1)] = int(match.group(2))
        for column in table.columns:
            if isinstance(column.type, sa.Integer) or isinstance(column.type, sa.Float):
                found[column.name].append(bounded.get(column.name))
    floored: dict[str, int] = {}
    for name, values in found.items():
        known = [value for value in values if value is not None]
        if values and len(known) == len(values) and min(known) >= 0:
            floored[name] = min(known)
    return floored


def belows(files: Mapping[Path, str], floored: Mapping[str, int]) -> list[Below]:
    return [
        Below(path, number, match.group(1))
        for path, text in files.items()
        for number, line in enumerate(text.splitlines(), start=1)
        for match in BELOW.finditer(line)
        if match.group(1) in floored and not guarded(text.splitlines(), number)
    ]


def guarded(lines: list[str], number: int) -> bool:
    return number < len(lines) and "raise " in lines[number]


def sources() -> dict[Path, str]:
    return {path: path.read_text(encoding="utf-8") for folder in SCANNED for path in sorted(folder.rglob("*.py"))}


def main() -> int:
    found = belows(sources(), floors())
    for item in found:
        print(
            f"{item.path.relative_to(ROOT)}:{item.line}: .{item.field} is compared below zero, but every column of that name is held at zero or "
            "above, so the test is never true; read the band or the threshold the scale is cut by"
        )
    print(f"negative scales: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
