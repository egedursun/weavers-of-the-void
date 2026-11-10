import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend" / "src"
WRAPPED = re.compile(r"className=['\"][^'\"]*\bflex-wrap\b[^'\"]*['\"][^>]*>\s*\{\(?([A-Za-z_][\w.?\[\]]*)\)?\.map\(")
PAGED_MARKS = ("visible", "shown")


@dataclass(frozen=True)
class Unpaged:
    path: Path
    line: int
    source: str


def bounded(source: str) -> bool:
    tail = source.rsplit(".", maxsplit=1)[-1].split("?", maxsplit=1)[0]
    constant = source.replace("_", "").replace(".", "").isupper()
    return constant or tail.endswith("Values") or any(mark in source for mark in PAGED_MARKS)


def unpaged_in(path: Path) -> list[Unpaged]:
    text = path.read_text(encoding="utf-8")
    return [Unpaged(path, text.count("\n", 0, match.start()) + 1, match.group(1)) for match in WRAPPED.finditer(text) if not bounded(match.group(1))]


def sources() -> list[Path]:
    return sorted(path for path in FRONTEND.rglob("*.tsx") if ".test." not in path.name and "generated" not in path.parts)


def main() -> int:
    found = [item for path in sources() for item in unpaged_in(path)]
    for item in found:
        print(f"{item.path.relative_to(ROOT)}:{item.line}: {item.source} is drawn in full in a wrapping row; page it with PagedList or useShowMore")
    print(f"unpaged lists: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
