import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "frontend" / "src"
BASE_TRIGGERS = frozenset({"AdjustPanel", "Button", "HoldButton"})
EXPORTED = re.compile(r"export function (\w+)\([^)]*\)[^{]*\{(.*?)\n\}", re.DOTALL)
ROOT_TAG = re.compile(r"return \(\s*<(\w+)")
COLUMN = re.compile(r"<div className='([^']*\bflex-col\b[^']*)'>")
TAG = re.compile(r"\s*<([A-Z]\w*)")
SPACED = re.compile(r"\bgap-|\bspace-y-")


def screens() -> list[Path]:
    return [path for path in sorted(ROOT.rglob("*.tsx")) if ".test." not in path.name]


def triggers(paths: list[Path]) -> frozenset[str]:
    found = set(BASE_TRIGGERS)
    for path in paths:
        for match in EXPORTED.finditer(path.read_text(encoding="utf-8")):
            root = ROOT_TAG.search(match.group(2))
            if root is not None and root.group(1) in BASE_TRIGGERS:
                found.add(match.group(1))
    return frozenset(found)


def children(lines: list[str], start: int) -> list[str]:
    indent = len(lines[start]) - len(lines[start].lstrip())
    found: list[str] = []
    for line in lines[start + 1 :]:
        depth = len(line) - len(line.lstrip())
        if depth <= indent and line.strip().startswith("</div>"):
            break
        tag = TAG.match(line)
        if depth == indent + 2 and tag is not None:
            found.append(tag.group(1))
    return found


def stacked(path: Path, known: frozenset[str]) -> list[str]:
    lines = path.read_text(encoding="utf-8").split("\n")
    problems: list[str] = []
    for index, line in enumerate(lines):
        column = COLUMN.search(line)
        if column is None or SPACED.search(column.group(1)):
            continue
        kids = [kid for kid in children(lines, index) if kid in known]
        if len(kids) >= 2:
            problems.append(f"{path.relative_to(ROOT.parent.parent)}:{index + 1}: {', '.join(kids)} stack with no gap between them; give the column a gap")
    return problems


def main() -> int:
    paths = screens()
    known = triggers(paths)
    problems = [problem for path in paths for problem in stacked(path, known)]
    for problem in problems:
        print(problem)
    print(f"stacked triggers: {len(problems)}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
