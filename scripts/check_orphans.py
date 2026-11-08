import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
USERS = (ROOT / "backend" / "tests", ROOT / "scripts", ROOT / "backend" / "src" / "aerona" / "db" / "alembic")
SKIPPED = frozenset({"alembic"})
DEFINITION = re.compile(r"^(?:async )?def ([a-zA-Z]\w*)\(|^([A-Z][A-Z0-9_]+)\s*(?::[^=\n]+)?=", re.M)
WORD = re.compile(r"\b\w+\b")


@dataclass(frozen=True)
class Orphan:
    path: Path
    line: int
    name: str


def sources() -> dict[Path, str]:
    return {path: path.read_text(encoding="utf-8") for path in sorted(SOURCE.rglob("*.py")) if not SKIPPED & set(path.parts)}


def decorated(text: str, start: int) -> bool:
    before = text[:start].rstrip("\n").rsplit("\n", 1)[-1].strip()
    return before.startswith("@") or before == ")"


def orphans(files: dict[Path, str], elsewhere: str) -> list[Orphan]:
    used = Counter(WORD.findall("\n".join(files.values()))) + Counter(WORD.findall(elsewhere))
    found: list[Orphan] = []
    for path, text in files.items():
        for match in DEFINITION.finditer(text):
            name = match.group(1) or match.group(2)
            if used[name] <= 1 and not decorated(text, match.start()):
                found.append(Orphan(path, text.count("\n", 0, match.start()) + 1, name))
    return found


def main() -> int:
    elsewhere = "\n".join(path.read_text(encoding="utf-8") for folder in USERS for path in sorted(folder.rglob("*.py")) if path.name != Path(__file__).name)
    found = orphans(sources(), elsewhere)
    for item in found:
        print(f"{item.path.relative_to(ROOT)}:{item.line}: {item.name} is defined but never used; wire it or delete it")
    print(f"orphans: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
