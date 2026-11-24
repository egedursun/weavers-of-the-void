import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "frontend" / "src"
FRAMED = re.compile(r"<(Card|OrnateFrame)\b(?P<props>[^>]*)>", re.DOTALL)
CLIPS = re.compile(r"\boverflow-(?:x-|y-)?(?:auto|hidden|scroll|clip)\b")


def clipped(text: str) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for match in FRAMED.finditer(text):
        clip = CLIPS.search(match.group("props"))
        if clip:
            found.append((text[: match.start()].count("\n") + 1, f"{match.group(1)} {clip.group(0)}"))
    return found


def problems() -> list[str]:
    found: list[str] = []
    for path in sorted(SOURCE.rglob("*.tsx")):
        if ".test." in path.name:
            continue
        for line, what in clipped(path.read_text(encoding="utf-8")):
            found.append(
                f"{path.relative_to(ROOT)}:{line}: {what} clips the frame's own corners; scroll or clip an inner element so the ornaments stay whole"
            )
    return found


def main() -> int:
    found = problems()
    print("\n".join(found))
    print(f"clipped frames: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
