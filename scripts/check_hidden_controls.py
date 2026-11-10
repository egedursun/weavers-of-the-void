import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend" / "src"
ACTING = re.compile(r"\.mutate\(|\bmutateAsync\(")
EMPTY_GATE = re.compile(r"\.length\s*(>|>=|!==|===)\s*\d|\.length\s*\?")
TERNARY_OPEN = re.compile(r"\?\s*\(")
PER_ITEM = re.compile(r"\.map\(|<Paged\b|\bitems=")


@dataclass(frozen=True)
class Hidden:
    path: Path
    line: int
    condition: str


def closing(text: str, start: int) -> int:
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
    return -1


def condition_before(text: str, start: int) -> str:
    opening = text.rfind("{", 0, start)
    return text[opening + 1 : start].strip() if opening >= 0 else ""


def hidden_in(path: Path) -> list[Hidden]:
    text = path.read_text(encoding="utf-8")
    found: list[Hidden] = []
    for match in TERNARY_OPEN.finditer(text):
        condition = condition_before(text, match.start())
        if "\n" in condition or not EMPTY_GATE.search(condition):
            continue
        first_end = closing(text, match.end() - 1)
        if first_end < 0:
            continue
        rest = text[first_end + 1 :].lstrip()
        if not rest.startswith(":"):
            continue
        second_start = text.index(":", first_end) + 1
        second_open = text.find("(", second_start)
        if second_open < 0 or text[second_start:second_open].strip():
            continue
        second_end = closing(text, second_open)
        if second_end < 0:
            continue
        present = text[match.end() : first_end]
        absent = text[second_open + 1 : second_end]
        acting = present if ACTING.search(present) and not ACTING.search(absent) else absent if ACTING.search(absent) and not ACTING.search(present) else ""
        if acting and not PER_ITEM.search(acting):
            found.append(Hidden(path, text.count("\n", 0, match.start()) + 1, condition))
    return found


def main() -> int:
    hidden = [item for path in sorted(FRONTEND.rglob("*.tsx")) if ".test." not in path.name for item in hidden_in(path)]
    for item in hidden:
        print(
            f"{item.path.relative_to(ROOT)}:{item.line}: a god control is replaced by a note when `{item.condition}`; keep the control and disable it with a reason"
        )
    print(f"hidden controls: {len(hidden)}")
    return 1 if hidden else 0


if __name__ == "__main__":
    sys.exit(main())
