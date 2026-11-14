import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
SCANNED = (SOURCE / "engine", SOURCE / "services", SOURCE / "agents", SOURCE / "tools", SOURCE / "api")
LEDGER = SOURCE / "engine" / "economy" / "stocks.py"
STOCK_SHIFT = re.compile(r"\.quantity\s*[-+]=")


@dataclass(frozen=True)
class Shift:
    path: Path
    line: int


def shifts(files: dict[Path, str]) -> list[Shift]:
    return [
        Shift(path, number)
        for path, text in files.items()
        if path != LEDGER
        for number, line in enumerate(text.splitlines(), start=1)
        if STOCK_SHIFT.search(line)
    ]


def sources() -> dict[Path, str]:
    return {path: path.read_text(encoding="utf-8") for folder in SCANNED for path in sorted(folder.rglob("*.py"))}


def main() -> int:
    found = shifts(sources())
    for item in found:
        print(
            f"{item.path.relative_to(ROOT)}:{item.line}: a stock quantity changes outside the goods ledger, so the flow is never logged and a held lot "
            "can be touched; move goods through goods_of(...).add, take, move or shift_lot"
        )
    print(f"goods ledger: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
