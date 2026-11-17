import ast
import datetime
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend/src/aerona"
FRONTEND = ROOT / "frontend/src"
LEDGER = ROOT / "docs/spec/model-text-ledger.md"
BACKEND_SCOPES = tuple(
    BACKEND / name for name in ("prompts", "tools", "agents", "catalog", "engine", "services", "epoch", "language", "cartography", "constants")
)
MODEL_FEEDING_FRONTEND = (FRONTEND / "features/onboarding",)
SKIPPED_FRONTEND = (FRONTEND / "api/generated",)
WORD = re.compile(r"[A-Za-z]{2,}")
PLACEHOLDER = re.compile(r"placeholder=(?:\{\s*)?(['\"`])((?:(?!\1).)*)\1", re.DOTALL)
QUOTED = re.compile(r"(['\"`])((?:\\.|(?!\1).)*)\1", re.DOTALL)
ROW = re.compile(r"^\| `([^`]+)` \| (\d+) \| (\d{4}-\d{2}-\d{2}) \| `([0-9a-f]{16})` \|$")
HEADER = (
    "# Model-facing text ledger",
    "",
    "Every file whose prose reaches the model or the chronicle, read in full against rule 2 of CLAUDE.md (spec 16 §47.14).",
    "A row is written with `scripts/check_text_ledger.py --record <file>` only after every string in the file was read and rewritten",
    "where it pushed a theme, tone, conflict, gender or look the seed did not ask for. The hash covers the file's prose,",
    "so any change to it after the read date fails the gate until the file is read again.",
    "",
    "| File | Strings | Read | Prose hash |",
    "|---|---|---|---|",
)


@dataclass(frozen=True)
class Entry:
    path: str
    strings: int
    read: str
    digest: str

    def render(self) -> str:
        return f"| `{self.path}` | {self.strings} | {self.read} | `{self.digest}` |"


def is_prose(value: str) -> bool:
    stripped = value.strip()
    return " " in stripped and len(WORD.findall(stripped)) >= 3


def python_strings(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    found = [(node.lineno, node.col_offset, node.value) for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)]
    return [value for _, _, value in sorted(found) if is_prose(value)]


def template_strings(path: Path) -> list[str]:
    return [line for line in path.read_text(encoding="utf-8").splitlines() if is_prose(line)]


def frontend_strings(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if any(path.is_relative_to(base) for base in MODEL_FEEDING_FRONTEND):
        return [match.group(2) for match in QUOTED.finditer(text) if is_prose(match.group(2))]
    return [match.group(2) for match in PLACEHOLDER.finditer(text) if match.group(2).strip()]


def targets() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for base in BACKEND_SCOPES:
        for path in sorted(base.rglob("*")):
            if "__pycache__" in path.parts or not path.is_file():
                continue
            strings = python_strings(path) if path.suffix == ".py" else template_strings(path) if path.suffix == ".j2" else []
            if strings:
                found[str(path.relative_to(ROOT))] = strings
    for path in sorted(FRONTEND.rglob("*")):
        if path.suffix not in {".ts", ".tsx"} or not path.is_file() or ".test." in path.name or any(path.is_relative_to(base) for base in SKIPPED_FRONTEND):
            continue
        strings = frontend_strings(path)
        if strings:
            found[str(path.relative_to(ROOT))] = strings
    return found


def digest(strings: list[str]) -> str:
    return hashlib.sha256("\n".join(strings).encode("utf-8")).hexdigest()[:16]


def read_ledger() -> dict[str, Entry]:
    if not LEDGER.exists():
        return {}
    entries: dict[str, Entry] = {}
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        match = ROW.match(line)
        if match:
            entries[match.group(1)] = Entry(match.group(1), int(match.group(2)), match.group(3), match.group(4))
    return entries


def write_ledger(entries: dict[str, Entry]) -> None:
    rows = [entries[key].render() for key in sorted(entries)]
    LEDGER.write_text("\n".join([*HEADER, *rows]) + "\n", encoding="utf-8")


def record(paths: list[str]) -> int:
    found = targets()
    entries = read_ledger()
    today = datetime.date.today().isoformat()
    missing = []
    for raw in paths:
        key = str(Path(raw).resolve().relative_to(ROOT)) if Path(raw).is_absolute() or Path(raw).exists() else raw
        if key not in found:
            missing.append(key)
            continue
        entries[key] = Entry(key, len(found[key]), today, digest(found[key]))
    write_ledger(entries)
    for key in missing:
        print(f"no model-facing prose in {key}; nothing recorded")
    return 0


def problems() -> list[str]:
    found = targets()
    entries = read_ledger()
    errors = [f"{key}: model-facing prose not yet read; read every string against rule 2, then record it" for key in sorted(set(found) - set(entries))]
    errors += [
        f"{key}: its prose changed after it was read on {entries[key].read}; read it again in full, then record it"
        for key in sorted(set(found) & set(entries))
        if digest(found[key]) != entries[key].digest
    ]
    errors += [f"{key}: in the ledger but holds no model-facing prose any more; drop its row" for key in sorted(set(entries) - set(found))]
    return errors


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--record":
        return record(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == "--pending":
        for line in problems():
            print(line.split(":", 1)[0])
        return 0
    errors = problems()
    for line in errors:
        print(line)
    print(f"text ledger: {len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
