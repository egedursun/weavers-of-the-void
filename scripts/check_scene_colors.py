import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "frontend" / "src"
SUFFIXES = (".ts", ".tsx")
RAW_STYLE = re.compile(r"\.setStyle\(")
RAW_READ = re.compile(r"new Color\(\s*(?:getComputedStyle|tokenValue|tokenString)|\.set\(\s*(?:getComputedStyle|tokenValue|tokenString)")


@dataclass(frozen=True)
class Raw:
    path: Path
    line: int
    text: str


def scan(text: str) -> list[int]:
    return [number for number, line in enumerate(text.splitlines(), start=1) if RAW_STYLE.search(line) or RAW_READ.search(line)]


def findings(root: Path = SOURCE) -> list[Raw]:
    found: list[Raw] = []
    for path in sorted(root.rglob("*")):
        if path.suffix not in SUFFIXES or ".test." in path.name or "generated" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        found.extend(Raw(path, number, text.splitlines()[number - 1].strip()) for number in scan(text))
    return found


def main() -> int:
    found = findings()
    for item in found:
        print(f"{item.path.relative_to(ROOT)}:{item.line}: a CSS colour reaches three.js unresolved; pass it through colorHex or tokenHex: {item.text}")
    print(f"raw scene colours: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
