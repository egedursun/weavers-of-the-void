import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOTS = (ROOT / "frontend" / "src",)
CLASS_TEXT = re.compile(r"""className=(?:'([^']*)'|"([^"]*)"|\{`([^`]*)`\})""")
RIGID = frozenset({"shrink-0", "flex-none", "flex-shrink-0"})


def sources() -> list[Path]:
    return sorted(
        path
        for root in SOURCE_ROOTS
        if root.exists()
        for path in root.rglob("*.tsx")
        if "node_modules" not in path.parts and not path.name.endswith(".test.tsx")
    )


def rigid_rows(text: str) -> list[int]:
    found: list[int] = []
    for match in CLASS_TEXT.finditer(text):
        classes = set(next(group for group in match.groups() if group is not None).split())
        if "flex-wrap" in classes and classes & RIGID:
            found.append(text.count("\n", 0, match.start()) + 1)
    return found


def main() -> int:
    problems = [f"{path.relative_to(ROOT)}:{line}" for path in sources() for line in rigid_rows(path.read_text(encoding="utf-8"))]
    for problem in problems:
        print(
            f"{problem} wraps its items but may not shrink (flex-wrap with shrink-0 or flex-none), so it keeps its widest size"
            " and its last items run out of the box on a narrow screen. Let it shrink (min-w-0) so its items wrap."
        )
    print(f"wrapping rows: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
