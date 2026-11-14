import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend" / "src"
VALUE_HOOKS = frozenset({"useState", "useRef", "useMemo", "useCallback", "useReducer", "useDeferredValue"})
CALL = re.compile(r"\b(use[A-Z]\w*)\(([^()]*\?\? 0)\)")


@dataclass(frozen=True)
class ZeroId:
    path: Path
    line: int
    text: str


def zero_ids(files: dict[Path, str]) -> list[ZeroId]:
    found: list[ZeroId] = []
    for path, text in files.items():
        for number, line in enumerate(text.splitlines(), start=1):
            found.extend(ZeroId(path, number, f"{hook}({argument})") for hook, argument in CALL.findall(line) if hook not in VALUE_HOOKS)
    return found


def screens() -> dict[Path, str]:
    return {path: path.read_text(encoding="utf-8") for path in sorted(FRONTEND.rglob("*.ts*")) if ".test." not in path.name}


def main() -> int:
    found = zero_ids(screens())
    for item in found:
        where = f"{item.path.relative_to(ROOT)}:{item.line}"
        print(f"{where}: {item.text} asks for record 0 while the id is missing; pass null and let the hook wait until there is an id")
    print(f"zero ids: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
