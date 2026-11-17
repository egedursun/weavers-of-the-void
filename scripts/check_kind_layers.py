import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from check_control import Code, levers, load_modules

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
ENUMS = SOURCE / "domain" / "enums"
TABLES = SOURCE / "db" / "tables"
LAYERS = SOURCE / "catalog" / "enum_layers.py"
CONCEPTS = SOURCE / "db" / "kind_concepts" / "registry.py"
KIND_SPECS = SOURCE / "db" / "kind_concepts"
FRONTEND = ROOT / "frontend" / "src"
LAYER_NAMES = ("authored", "closed", "process")
ENUM_BASES = frozenset({"StrEnum", "Enum", "IntEnum"})
ENUM_COLUMN = re.compile(r"(\w+): Mapped\[[^\]]*\] = mapped_column\((?:['\"]\w+['\"],\s*)?enum_type\((\w+),")
NODE_LINK = re.compile(r"ForeignKey\(['\"](?:nodes|entities|worlds|sons|foreign_gods)\.id['\"]")


@dataclass(frozen=True)
class Declared:
    layer: str
    reason: str
    table: str | None
    concept: str | None


@dataclass(frozen=True)
class KindTable:
    name: str
    row_class: str
    enums: dict[str, str]
    properties: int
    linked: bool


@dataclass(frozen=True)
class Problem:
    enum: str
    why: str


def parsed(path: Path) -> ast.Module:
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return ast.Module(body=[], type_ignores=[])


def enum_members(path: Path) -> dict[str, list[tuple[str, str]]]:
    found: dict[str, list[tuple[str, str]]] = {}
    for node in parsed(path).body:
        if isinstance(node, ast.ClassDef) and any(isinstance(base, ast.Name) and base.id in ENUM_BASES for base in node.bases):
            members = []
            for item in node.body:
                if isinstance(item, ast.Assign) and len(item.targets) == 1 and isinstance(item.targets[0], ast.Name):
                    value = item.value.value if isinstance(item.value, ast.Constant) else item.targets[0].id.lower()
                    members.append((item.targets[0].id, str(value)))
            found[node.name] = members
    return found


def all_enums(folder: Path = ENUMS) -> dict[str, list[tuple[str, str]]]:
    found: dict[str, list[tuple[str, str]]] = {}
    for path in sorted(folder.glob("*.py")):
        if path.name == "__init__.py":
            continue
        for name, members in enum_members(path).items():
            found[f"{path.stem}.{name}"] = members
    return found


def declared(path: Path = LAYERS) -> dict[str, Declared]:
    if not path.exists():
        return {}
    found: dict[str, Declared] = {}
    for node in ast.walk(parsed(path)):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values, strict=True):
                if isinstance(key, ast.Constant) and isinstance(value, ast.Call):
                    args = [arg.value if isinstance(arg, ast.Constant) else None for arg in value.args]
                    keywords = {item.arg: item.value.value for item in value.keywords if isinstance(item.value, ast.Constant)}
                    args += [None] * (4 - len(args))
                    found[str(key.value)] = Declared(
                        str(keywords.get("layer", args[0])),
                        str(keywords.get("reason", args[1])),
                        keywords.get("table", args[2]),
                        keywords.get("concept", args[3]),
                    )
    return found


def kind_tables(folder: Path = TABLES) -> dict[str, KindTable]:
    found: dict[str, KindTable] = {}
    for path in sorted(folder.glob("*.py")):
        for node in parsed(path).body:
            if not isinstance(node, ast.ClassDef):
                continue
            text = ast.unparse(node)
            name = next(
                (
                    item.value.value
                    for item in node.body
                    if isinstance(item, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == "__tablename__" for target in item.targets)
                    and isinstance(item.value, ast.Constant)
                ),
                None,
            )
            if name is None:
                continue
            properties = sum(
                1
                for item in node.body
                if isinstance(item, ast.AnnAssign)
                and ast.unparse(item.annotation) in ("Mapped[int]", "Mapped[int | None]", "Mapped[float]", "Mapped[bool]")
                and "primary_key=True" not in ast.unparse(item)
                and "ForeignKey" not in ast.unparse(item)
            )
            inherited = any(isinstance(base, ast.Name) and base.id == "KindRow" for base in node.bases)
            found[str(name)] = KindTable(
                str(name), node.name, {enum: column for column, enum in ENUM_COLUMN.findall(text)}, properties, bool(NODE_LINK.search(text)) or inherited
            )
    return found


def enum_aliases(tree: ast.Module, known: dict[str, str]) -> dict[str, str]:
    found: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("aerona.domain.enums."):
            stem = node.module.rsplit(".", 1)[1]
            for alias in node.names:
                key = f"{stem}.{alias.name}"
                if key in known:
                    found[alias.asname or alias.name] = key
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Name):
            if node.value.id in found:
                found[node.targets[0].id] = found[node.value.id]
    return found


def catalogued(source: Path = SOURCE, known: dict[str, list[tuple[str, str]]] | None = None) -> set[str]:
    known = all_enums() if known is None else known
    members = {name.split(".")[1]: {member for member, _ in values} for name, values in known.items()}
    found: set[str] = set()
    for path in sorted(source.rglob("*.py")):
        if "alembic" in path.parts or "__pycache__" in path.parts or "defined" in path.parts or path.parent.name == "enums":
            continue
        tree = parsed(path)
        aliases = {alias: key.split(".")[1] for alias, key in enum_aliases(tree, {name: name for name in known}).items()}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") in ("total", "partial") and node.args and isinstance(node.args[0], ast.Name):
                found.add(aliases.get(node.args[0].id, node.args[0].id))
            elif isinstance(node, ast.Dict) and node.keys:
                owners = {aliases.get(key.value.id) for key in node.keys if isinstance(key, ast.Attribute) and isinstance(key.value, ast.Name)}
                if len(owners) == 1 and None not in owners and len(node.keys) == sum(1 for key in node.keys if isinstance(key, ast.Attribute)):
                    owner = owners.pop()
                    if owner is not None and {key.attr for key in node.keys if isinstance(key, ast.Attribute)} >= members.get(owner, {""}):
                        found.add(owner)
    return found


def registered_definitions(folder: Path = SOURCE / "catalog" / "kinds" / "defined") -> set[str]:
    index = folder / "__init__.py"
    if not index.exists():
        return set()
    return set(re.findall(r'^\s*"([\w.]+)":', index.read_text(encoding="utf-8"), re.M))


def concept_tables(concepts: Path = CONCEPTS, specs: Path = KIND_SPECS) -> set[str]:
    rows: set[str] = set()
    for path in sorted(specs.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        rows |= set(re.findall(r"table=(\w+Row)", text))
    return rows


def source_text(folder: Path, suffixes: tuple[str, ...]) -> str:
    return "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(folder.rglob("*")) if path.suffix in suffixes and path.is_file() and "generated" not in path.parts
    )


def inherited_tables(code: Code) -> dict[str, set[str]]:
    parents: dict[str, set[str]] = {}
    for name, tree in code.modules.items():
        if not name.startswith("aerona.db.tables"):
            continue
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name in code.rows:
                bases = {code.rows[base.id] for base in node.bases if isinstance(base, ast.Name) and base.id in code.rows}
                if bases:
                    parents[code.rows[node.name]] = bases
    return parents


def with_parents(tables: set[str], parents: dict[str, set[str]]) -> set[str]:
    found = set(tables)
    frontier = list(tables)
    while frontier:
        for parent in parents.get(frontier.pop(), set()):
            if parent not in found:
                found.add(parent)
                frontier.append(parent)
    return found


@dataclass(frozen=True)
class Reach:
    levers: frozenset[str]
    tools: frozenset[str]


def reached() -> Reach:
    code = Code(load_modules())
    lever_tables: set[str] = set()
    for key in levers(code).values():
        for tables in code.reach(key).values():
            lever_tables |= tables
    tool_tables: set[str] = set()
    for name, tree in code.modules.items():
        if not name.startswith("aerona.tools."):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "ToolSpec" and len(node.args) > 4 and isinstance(node.args[4], ast.Name):
                key = code.resolve(name, node.args[4].id)
                if key is not None:
                    for tables in code.reach(key).values():
                        tool_tables |= tables
    parents = inherited_tables(code)
    return Reach(frozenset(with_parents(lever_tables, parents)), frozenset(with_parents(tool_tables, parents)))


@dataclass(frozen=True)
class Surfaces:
    tables: dict[str, KindTable]
    concept_rows: set[str]
    reach: Reach
    tools: str
    screens: str
    defined: set[str]


def authored_problems(name: str, entry: Declared, seen: Surfaces) -> list[str]:
    tables, concept_rows, reach, tools, screens, defined = seen.tables, seen.concept_rows, seen.reach, seen.tools, seen.screens, seen.defined
    enum = name.split(".")[1]
    if entry.table is None:
        return ["is declared authored but names no kind table"]
    table = tables.get(entry.table)
    if table is None:
        return [f"names the kind table {entry.table}, which does not exist"]
    found: list[str] = []
    if enum not in table.enums:
        found.append(f"is not a column of its kind table {entry.table}")
    if table.properties == 0 and enum not in defined:
        found.append(f"has a kind table {entry.table} with no typed properties and no property catalogue")
    generic = table.row_class in concept_rows
    if not (generic or table.linked or table.name in reach.levers):
        found.append(f"has no god lever over {entry.table}")
    if not (generic or table.name in reach.tools or re.search(rf"\b{enum}\b", tools)):
        found.append(f"is reached by no agent tool ({entry.table})")
    column = table.enums.get(enum, "")
    shown = rf"\['{enum}'\]|\"{enum}\"|'{enum}'|\b{enum[0].lower()}{enum[1:]}Values\b|\b{entry.table}\b" + (rf"|\.{column}\b|\b{column}:" if column else "")
    if not (generic or re.search(shown, screens)):
        found.append("is shown and set by no screen")
    return found


def contradicts(entry: Declared) -> bool:
    named = entry.reason.split(":", 1)[0].strip()
    return named in LAYER_NAMES and named != entry.layer


def problems() -> list[Problem]:
    enums = all_enums()
    layers = declared()
    tables = kind_tables()
    concept_rows = concept_tables()
    tools = source_text(SOURCE / "tools", (".py",))
    screens = source_text(FRONTEND, (".ts", ".tsx"))
    defined = catalogued() | {name.split(".")[1] for name in registered_definitions()}
    seen = Surfaces(tables, concept_rows, reached(), tools, screens, defined)
    found = [Problem(name, "is not declared in catalog/enum_layers.py") for name in sorted(set(enums) - set(layers))]
    found += [Problem(name, "is declared but no longer exists") for name in sorted(set(layers) - set(enums))]
    claims: dict[str, list[str]] = {}
    for name, entry in sorted(layers.items()):
        if name not in enums:
            continue
        if entry.layer not in LAYER_NAMES:
            found.append(Problem(name, f"has the unknown layer {entry.layer}"))
            continue
        if not entry.reason.strip():
            found.append(Problem(name, "gives no reason for its layer"))
        elif contradicts(entry):
            found.append(Problem(name, f"is declared {entry.layer} but its reason names another layer: {entry.reason}"))
        if entry.concept is not None:
            claims.setdefault(entry.concept, []).append(name)
        if entry.layer == "authored":
            found += [Problem(name, why) for why in authored_problems(name, entry, seen)]
    for concept, names in sorted(claims.items()):
        if len(names) > 1:
            found += [Problem(name, f"claims the concept {concept} with {', '.join(other for other in names if other != name)}") for name in names]
    return found


def main() -> int:
    found = problems()
    for item in found:
        print(f"{item.enum}: {item.why}")
    print(f"kind layers: {len(found)} problem(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
