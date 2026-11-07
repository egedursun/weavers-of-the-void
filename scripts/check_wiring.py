import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend/src/aerona"
ENUMS = BACKEND / "domain/enums"
TABLES = BACKEND / "db/tables"
CATALOG = BACKEND / "services/player/catalog.py"
COMPLIANCE = BACKEND / "engine/interconnect/compliance.py"
ENGINE = BACKEND / "engine"
CONTROL_CONSTANTS = BACKEND / "constants/control.py"
BOOKKEEPING_TABLES = frozenset(re.findall(r'"([a-z_]+)"', CONTROL_CONSTANTS.read_text(encoding="utf-8")))
FRONTEND = ROOT / "frontend/src"
SKIPPED_PARTS = frozenset({"__pycache__", "alembic"})
ENUM_BASES = frozenset({"StrEnum", "IntEnum", "Enum"})


def backend_texts() -> dict[Path, str]:
    return {path: path.read_text(encoding="utf-8") for path in BACKEND.rglob("*.py") if not SKIPPED_PARTS.intersection(path.parts)}


def frontend_source(path: Path) -> bool:
    return path.suffix in {".ts", ".tsx"} and path.is_file() and not {"generated", "__screenshots__"}.intersection(path.parts) and ".test." not in path.name


def frontend_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in FRONTEND.rglob("*") if frontend_source(path))


WORD = re.compile(r"\w+")
WORD_HOMES: dict[str, frozenset[Path]] = {}


def word_homes(texts: dict[Path, str]) -> dict[str, frozenset[Path]]:
    if not WORD_HOMES:
        homes: dict[str, set[Path]] = {}
        for path, text in texts.items():
            for word in set(WORD.findall(text)):
                homes.setdefault(word, set()).add(path)
        WORD_HOMES.update({word: frozenset(paths) for word, paths in homes.items()})
    return WORD_HOMES


def used_elsewhere(name: str, home: Path, texts: dict[Path, str]) -> bool:
    return bool(word_homes(texts).get(name, frozenset()) - {home})


def orphan_enums(texts: dict[Path, str]) -> list[str]:
    found: list[str] = []
    for path in sorted(ENUMS.rglob("*.py")):
        for node in ast.parse(texts[path]).body:
            enum = isinstance(node, ast.ClassDef) and any(getattr(base, "id", "") in ENUM_BASES for base in node.bases)
            if enum and isinstance(node, ast.ClassDef) and not used_elsewhere(node.name, path, texts):
                found.append(f"{path.relative_to(ROOT)}: enum {node.name} is defined but never used")
    return found


def orphan_tables(texts: dict[Path, str]) -> list[str]:
    homes = word_homes(texts)
    found: list[str] = []
    for path in sorted(TABLES.rglob("*.py")):
        for name in re.findall(r"^class (\w+Row)\(", texts[path], re.MULTILINE):
            if not any(not home.is_relative_to(TABLES) for home in homes.get(name, frozenset())):
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


def table_names(texts: dict[Path, str]) -> dict[str, str]:
    names: dict[str, str] = {}
    for path, text in texts.items():
        if path.is_relative_to(TABLES):
            for node in ast.parse(text).body:
                if isinstance(node, ast.ClassDef):
                    for item in node.body:
                        named = isinstance(item, ast.Assign) and any(getattr(target, "id", "") == "__tablename__" for target in item.targets)
                        if named and isinstance(item, ast.Assign) and isinstance(item.value, ast.Constant):
                            names[node.name] = str(item.value.value)
    return names


def strings_of(node: ast.expr, names: dict[str, str]) -> list[str]:
    if not isinstance(node, ast.Tuple):
        return []
    found: list[str] = []
    for item in node.elts:
        if isinstance(item, ast.Constant) and isinstance(item.value, str):
            found.append(item.value)
        elif isinstance(item, ast.Attribute) and item.attr == "__tablename__" and isinstance(item.value, ast.Name) and item.value.id in names:
            found.append(names[item.value.id])
    return found


def controlled_tables(texts: dict[Path, str], names: dict[str, str]) -> set[str]:
    registered = set(re.findall(r'Meta\(\s*"([^"]+)"', texts[CATALOG]))
    controlled: set[str] = set()
    for node in ast.walk(ast.parse(texts[COMPLIANCE])):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "ComplianceRow" and len(node.args) >= 4:
            levers = [lever for lever in strings_of(node.args[3], names) if lever in registered]
            if levers:
                controlled.update(strings_of(node.args[1], names))
    return controlled


def uncontrolled_tables(texts: dict[Path, str]) -> list[str]:
    names = table_names(texts)
    known = set(names.values())
    written = {name for path, text in texts.items() if path.is_relative_to(ENGINE) for name in re.findall(r'"table\.([a-z_]+)"', text)}
    controlled = controlled_tables(texts, names)
    return [
        f"table {name} is written by the engine but no compliance row gives the god a registered lever to create, edit, hold or delete it"
        for name in sorted(written & known)
        if name not in controlled and name not in BOOKKEEPING_TABLES
    ]


NODE_ENUM = BACKEND / "domain/enums/node.py"
DRAWER_PAGES = FRONTEND / "config/drawerPages.ts"
SHARED_SECTIONS = "<ThingSections"


def node_kinds() -> set[str]:
    text = NODE_ENUM.read_text(encoding="utf-8")
    body = text.split("class NodeKind", 1)[1].split("\nclass ", 1)[0]
    return set(re.findall(r'=\s*"([a-z_]+)"', body))


def module_file(spec: str, origin: Path) -> Path | None:
    base = FRONTEND / spec.removeprefix("@/") if spec.startswith("@/") else (origin.parent / spec).resolve() if spec.startswith(".") else None
    if base is None:
        return None
    return next((path for path in (base.with_suffix(".tsx"), base.with_suffix(".ts"), base / "index.ts") if path.is_file()), None)


def component_body(text: str, name: str) -> str:
    match = re.search(rf"^(?:export )?function {name}\(", text, re.MULTILINE)
    if match is None:
        return ""
    end = re.search(r"^(?:export )?function \w+\(", text[match.end() :], re.MULTILINE)
    return text[match.start() : match.end() + end.start() if end else len(text)]


def component_renders_shared(text: str, name: str, depth: int = 4) -> bool:
    body = component_body(text, name)
    if SHARED_SECTIONS in body:
        return True
    inner = {found for found in re.findall(r"<([A-Z]\w*)", body) if found != name and component_body(text, found)}
    return depth > 0 and any(component_renders_shared(text, found, depth - 1) for found in inner)


def renders_shared(page: Path) -> bool:
    text = page.read_text(encoding="utf-8")
    if SHARED_SECTIONS in text:
        return True
    for names, spec in re.findall(r"import \{([^}]+)\} from '([^']+)'", text):
        path = module_file(spec, page)
        rendered = [name.strip() for name in names.split(",") if f"<{name.strip()}" in text]
        if path is not None and any(component_renders_shared(path.read_text(encoding="utf-8"), name) for name in rendered):
            return True
    return False


def pages_without_shared_sections() -> list[str]:
    kinds = node_kinds()
    found: list[str] = []
    for kind, spec in re.findall(r"['\"]?([a-z-]+)['\"]?:\s*lazy\(\(\)\s*=>\s*import\('([^']+)'\)", DRAWER_PAGES.read_text(encoding="utf-8")):
        if kind.replace("-", "_") not in kinds:
            continue
        page = module_file(spec, DRAWER_PAGES)
        if page is None or not renders_shared(page):
            found.append(f"the {kind} drawer page does not render ThingSections, so features shared by every thing are missing there")
    return found


BOOKS = BACKEND / "services/books"
TYPED = BOOKS / "typed.py"
BOOK_TEMPLATES = (BOOKS / "templates/book.html.j2", BOOKS / "templates/macros.html.j2")
CODEX_TEMPLATE = BOOKS / "templates/codex.md.j2"
BOOK_SECTIONS = (
    "typed(article.typed)",
    "typed(world.typed)",
    "typed(section.typed)",
    "typed(book.creator_typed)",
    "records(book.records)",
)


def frozen_names(text: str, name: str) -> set[str]:
    found = re.search(rf"{name} = frozenset\(\s*\{{([^}}]*)\}}", text)
    return set(re.findall(r'"([a-z_]+)"', found.group(1))) if found else set()


def node_tables(texts: dict[Path, str], names: dict[str, str]) -> set[str]:
    kinds: set[str] = set()
    for path, text in texts.items():
        if path.is_relative_to(TABLES):
            for node in ast.parse(text).body:
                if isinstance(node, ast.ClassDef) and any(getattr(base, "id", "") == "NodeRow" for base in node.bases) and node.name in names:
                    kinds.add(names[node.name])
    return kinds | {"nodes"}


def book_gaps(texts: dict[Path, str]) -> list[str]:
    names = table_names(texts)
    classes = {table: name for name, table in names.items()}
    typed = TYPED.read_text(encoding="utf-8")
    skipped = frozen_names(typed, "SKIPPED_TABLES")
    owners = frozen_names(typed, "OWNER_TABLES")
    rendered = "\n".join(text for path, text in texts.items() if path.is_relative_to(BOOKS) and path != TYPED)
    errors = [
        f"table {table} is kept out of the generic book records but no book or codex code renders {classes.get(table, table)}"
        for table in sorted(skipped)
        if table in classes and not re.search(rf"\b{classes[table]}\b", rendered)
    ]
    errors += [
        f"table {table} is a kind of node but its records never reach its book and codex entry (add it to OWNER_TABLES)"
        for table in sorted(node_tables(texts, names) - owners)
    ]
    book = "\n".join(path.read_text(encoding="utf-8") for path in BOOK_TEMPLATES)
    codex = CODEX_TEMPLATE.read_text(encoding="utf-8")
    for snippet in BOOK_SECTIONS:
        errors += [f"{label} does not render {snippet}" for label, text in (("the lore book", book), ("the codex", codex)) if snippet not in text]
    return errors


def main() -> int:
    texts = backend_texts()
    errors = [
        *orphan_enums(texts),
        *orphan_tables(texts),
        *unregistered_actions(texts),
        *actions_without_ui(texts, frontend_text()),
        *uncontrolled_tables(texts),
        *pages_without_shared_sections(),
        *book_gaps(texts),
    ]
    for line in errors:
        print(f"ERROR {line}")
    print(f"wiring: {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
