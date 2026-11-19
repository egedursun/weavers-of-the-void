import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "docs" / "spec"
sys.path.insert(0, str(ROOT / "backend" / "src"))

from aerona.db import tables
from aerona.db.base import Base

assert tables

LISTS = ("ocm-coverage.md", "science-coverage.md", "motif-coverage.md")
COVERAGE = SPEC / "16-coverage.md"
WAVE_SPEC = SPEC / "16-minds-powers-living-craft.md"
SECTION = re.compile(r"\b(50\.\d+)\b")
TABLE = re.compile(r"`([a-z][a-z0-9_]*)`")
COMPLIANCE_HEAD = "### 50.18 Compliance catalogue (W50)"


@dataclass(frozen=True)
class Item:
    source: str
    code: str
    name: str
    closed_by: str


def items(folder: Path = SPEC) -> list[Item]:
    found: list[Item] = []
    for name in LISTS:
        for line in (folder / name).read_text(encoding="utf-8").splitlines():
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) != 4 or cells[0] in {"OCM", "Code", "Range"} or set(cells[0]) <= {"-"}:
                continue
            found.append(Item(name, cells[0], cells[1], cells[3]))
    return found


def statuses(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) > 2 and cells[0].startswith("S50."):
            found[cells[0].removeprefix("S")] = cells[-1]
    return found


def compliance_tables(text: str) -> dict[str, set[str]]:
    lines = text.splitlines()
    start = next(index for index, line in enumerate(lines) if line.startswith(COMPLIANCE_HEAD))
    found: dict[str, set[str]] = {}
    for line in lines[start + 1 :]:
        if line.startswith("#"):
            break
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2 or not cells[0][:1].isdigit():
            continue
        section = cells[0].split()[0]
        found[section] = set(TABLE.findall(cells[1]))
    return found


def problems(found: list[Item], status: dict[str, str], declared: dict[str, set[str]], known: set[str]) -> list[str]:
    lines: list[str] = []
    for item in found:
        where = f"{item.source} {item.code} {item.name}"
        if not item.closed_by:
            lines.append(f"{where}: no closing section")
            continue
        for section in sorted(set(SECTION.findall(item.closed_by))):
            state = status.get(section)
            if state is None:
                lines.append(f"{where}: closed by {section}, which has no coverage row")
            elif state != "done":
                lines.append(f"{where}: closed by {section}, still {state}")
            else:
                missing = sorted(declared.get(section, set()) - known)
                if missing:
                    lines.append(f"{where}: {section} is done but names missing tables {', '.join(missing)}")
    return lines


def main() -> int:
    found = items()
    status = statuses(COVERAGE.read_text(encoding="utf-8"))
    declared = compliance_tables(WAVE_SPEC.read_text(encoding="utf-8"))
    lines = problems(found, status, declared, set(Base.metadata.tables))
    for line in lines:
        print(line)
    print(f"ocm coverage: {len(found)} items, {len(lines)} problem(s)")
    return 1 if lines else 0


if __name__ == "__main__":
    raise SystemExit(main())
