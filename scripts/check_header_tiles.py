import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = ROOT / "frontend" / "src"
ACTIONS = re.compile(r"\bactions=\{")
FRAMED_TILE = re.compile(r"<FieldTile\b(?![^>]*framed=\{false\})")


def sources() -> list[Path]:
    if not SOURCE_ROOT.exists():
        return []
    return sorted(path for path in SOURCE_ROOT.rglob("*.tsx") if path.is_file() and ".test." not in path.name and "generated" not in path.parts)


def framed_in_actions(code: str) -> list[int]:
    found: list[int] = []
    for match in ACTIONS.finditer(code):
        depth, end = 1, match.end()
        while depth and end < len(code):
            depth += {"{": 1, "}": -1}.get(code[end], 0)
            end += 1
        if FRAMED_TILE.search(code[match.end() : end]):
            found.append(code.count("\n", 0, match.start()) + 1)
    return found


def problems() -> list[str]:
    return [f"{path.relative_to(ROOT)}:{line}" for path in sources() for line in framed_in_actions(path.read_text(encoding="utf-8"))]


def main() -> int:
    found = problems()
    for problem in found:
        print(
            f"{problem} puts a framed FieldTile among a header's actions."
            " The tile stacks its label over the control in a gilded box, taller than the buttons beside it, so the header row breaks."
            " Put a switch with its label inline, or pass framed={false} with a row layout."
        )
    print(f"header tiles: {len(found)} problem(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
