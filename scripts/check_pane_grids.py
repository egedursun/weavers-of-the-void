import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend" / "src"
PANES = (FRONTEND / "features" / "atlas", FRONTEND / "features" / "madeKinds", FRONTEND / "features" / "cosmography" / "parts.tsx")
VIEWPORT_GRID = re.compile(r"(?<![@\w/-])(?:sm|md|lg|xl|2xl):(?:grid-cols|col-span)-")


def viewport_grids_in(text: str) -> list[int]:
    return [index for index, line in enumerate(text.splitlines(), start=1) if VIEWPORT_GRID.search(line)]


def pane_files() -> list[Path]:
    found: list[Path] = []
    for pane in PANES:
        found.extend([pane] if pane.is_file() else sorted(pane.rglob("*.tsx")))
    return [path for path in found if ".test." not in path.name]


def main() -> int:
    found = [
        f"{path.relative_to(ROOT)}:{line}: a grid inside a pane splits by the width of the screen; split it by its container (@container and @sm:, @md:…)"
        for path in pane_files()
        for line in viewport_grids_in(path.read_text(encoding="utf-8"))
    ]
    print("\n".join(found))
    print(f"pane grids: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
