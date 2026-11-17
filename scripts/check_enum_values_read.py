import ast
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
ENUMS = SOURCE / "domain" / "enums"
READERS = (
    "engine",
    "catalog",
    "rules",
    "services",
    "agents",
    "tools",
    "core",
    "db/write_guard.py",
    "jobs",
    "cartography",
    "migration",
    "epoch",
    "events",
    "imaging",
    "language",
    "llm",
    "media",
    "constants",
    "api/routers",
    "api/views",
    "db/repositories",
    "db/kind_concepts",
)
ITERATING = frozenset(
    {
        "list",
        "tuple",
        "set",
        "frozenset",
        "sorted",
        "len",
        "total",
        "partial",
        "enumerate",
        "next",
        "iter",
    }
)


def enum_members() -> dict[str, dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    for path in sorted(ENUMS.glob("*.py")):
        for node in ast.parse(path.read_text()).body:
            if isinstance(node, ast.ClassDef) and any(isinstance(base, ast.Name) and base.id in {"StrEnum", "IntEnum", "Enum"} for base in node.bases):
                members = {
                    target.id: str(statement.value.value)
                    for statement in node.body
                    if isinstance(statement, ast.Assign) and isinstance(statement.value, ast.Constant)
                    for target in statement.targets
                    if isinstance(target, ast.Name)
                }
                found[node.name] = members
    return found


def reader_files() -> list[Path]:
    files: list[Path] = []
    for name in READERS:
        path = SOURCE / name
        files.extend([path] if path.is_file() else sorted(path.rglob("*.py")) if path.is_dir() else [])
    return [path for path in files if "__pycache__" not in path.parts]


def aliases_in(tree: ast.Module, enums: dict[str, dict[str, str]]) -> dict[str, str]:
    aliases = {name: name for name in enums}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Name) and node.value.id in enums:
            aliases.update({target.id: node.value.id for target in node.targets if isinstance(target, ast.Name)})
        if isinstance(node, ast.ImportFrom):
            aliases.update({alias.asname: alias.name for alias in node.names if alias.name in enums and alias.asname})
    return aliases


def iterated_name(node: ast.AST, aliases: dict[str, str]) -> str | None:
    loop = node.iter if isinstance(node, ast.For | ast.comprehension) else None
    if isinstance(loop, ast.Name) and loop.id in aliases:
        return aliases[loop.id]
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
        return None
    if node.func.id in aliases and node.args and not isinstance(node.args[0], ast.Constant):
        return aliases[node.func.id]
    if node.func.id in ITERATING:
        return next(
            (aliases[argument.id] for argument in node.args if isinstance(argument, ast.Name) and argument.id in aliases),
            None,
        )
    return None


def reads(enums: dict[str, dict[str, str]]) -> tuple[dict[str, set[str]], set[str]]:
    used: dict[str, set[str]] = defaultdict(set)
    iterated: set[str] = set()
    for path in reader_files():
        tree = ast.parse(path.read_text())
        aliases = aliases_in(tree, enums)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in aliases:
                used[aliases[node.value.id]].add(node.attr)
            elif (name := iterated_name(node, aliases)) is not None:
                iterated.add(name)
    return used, iterated


def unread() -> list[str]:
    enums = enum_members()
    used, iterated = reads(enums)
    return [
        f"{name}.{member} ({value})"
        for name, members in sorted(enums.items())
        if name not in iterated
        for member, value in sorted(members.items())
        if member not in used[name]
    ]


def main() -> int:
    found = unread()
    for line in found:
        print(f"unread enum value: {line}; give it behaviour where the engine reads it, or remove it")
    print(f"unread enum values: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
