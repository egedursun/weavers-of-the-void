import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "frontend" / "src"
SWEEP = re.compile(r"\buseAllEntities\(")
TYPE_PICK = re.compile(r"entity_type\s*===\s*['\"\w]|ranked\([^)]*['\"]\w+['\"]")


def sources() -> list[Path]:
    return sorted(path for path in SOURCE.rglob("*.tsx") if ".test." not in path.name)


def picks_types_from_a_sweep(text: str) -> bool:
    return SWEEP.search(text) is not None and TYPE_PICK.search(text) is not None


def main() -> int:
    problems = [str(path.relative_to(ROOT)) for path in sources() if picks_types_from_a_sweep(path.read_text(encoding="utf-8"))]
    for problem in problems:
        print(
            f"{problem} reads every record with useAllEntities and keeps only some kinds, so the screen waits for every page of"
            " every record. Ask the server for those kinds with useEntitiesOfType."
        )
    print(f"entity sweeps: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
