import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend/src/aerona"
ENUMS = BACKEND / "domain/enums"
TABLES = BACKEND / "db/tables"
CATALOG = BACKEND / "services/player/catalog.py"
FRONTEND = ROOT / "frontend/src"
SKIPPED_PARTS = frozenset({"__pycache__", "alembic"})
ENUM_BASES = frozenset({"StrEnum", "IntEnum", "Enum"})


def backend_texts() -> dict[Path, str]:
    return {path: path.read_text(encoding="utf-8") for path in BACKEND.rglob("*.py") if not SKIPPED_PARTS.intersection(path.parts)}


def frontend_source(path: Path) -> bool:
    return path.suffix in {".ts", ".tsx"} and path.is_file() and not {"generated", "__screenshots__"}.intersection(path.parts) and ".test." not in path.name


def frontend_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in FRONTEND.rglob("*") if frontend_source(path))


def used_elsewhere(name: str, home: Path, texts: dict[Path, str]) -> bool:
    pattern = re.compile(rf"\b{name}\b")
    return any(path != home and pattern.search(text) for path, text in texts.items())


def orphan_enums(texts: dict[Path, str]) -> list[str]:
    found: list[str] = []
    for path in sorted(ENUMS.rglob("*.py")):
        for node in ast.parse(texts[path]).body:
            enum = isinstance(node, ast.ClassDef) and any(getattr(base, "id", "") in ENUM_BASES for base in node.bases)
            if enum and isinstance(node, ast.ClassDef) and not used_elsewhere(node.name, path, texts):
                found.append(f"{path.relative_to(ROOT)}: enum {node.name} is defined but never used")
    return found


def orphan_tables(texts: dict[Path, str]) -> list[str]:
    outside = {path: text for path, text in texts.items() if not path.is_relative_to(TABLES)}
    found: list[str] = []
    for path in sorted(TABLES.rglob("*.py")):
        for name in re.findall(r"^class (\w+Row)\(", texts[path], re.MULTILINE):
            if not any(re.search(rf"\b{name}\b", text) for text in outside.values()):
                found.append(f"{path.relative_to(ROOT)}: table {name} is never read or written outside db/tables")
    return found


def unregistered_actions(texts: dict[Path, str]) -> list[str]:
    registered = set(re.findall(r'Meta\(\s*"([^"]+)"', texts[CATALOG]))
    found: list[str] = []
    for path, text in sorted(texts.items()):
        for action in re.findall(r'@player_action\(\s*"([^"]+)"', text):
            if action not in registered:
                found.append(f"{path.relative_to(ROOT)}: player action {action} is not in the action catalog, so no API or UI can reach it")
    return found


def actions_without_ui(texts: dict[Path, str], frontend: str) -> list[str]:
    catalog = texts[CATALOG]
    typed = set(re.findall(r'Alias\(\s*"[A-Z]+",\s*"[^"]+",\s*"([^"]+)"', "\n".join(texts.values())))
    found: list[str] = []
    for action in sorted(set(re.findall(r'Meta\(\s*"([^"]+)"', catalog))):
        if action in frontend:
            continue
        if action in typed:
            continue
        found.append(f"action {action} has no frontend caller")
    return found


def main() -> int:
    texts = backend_texts()
    errors = [*orphan_enums(texts), *orphan_tables(texts), *unregistered_actions(texts), *actions_without_ui(texts, frontend_text())]
    for line in errors:
        print(f"ERROR {line}")
    print(f"wiring: {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
