import ast
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from check_kind_layers import FRONTEND, ROOT, SOURCE, all_enums, catalogued, declared, enum_aliases, parsed, registered_definitions

DEFINED = SOURCE / "catalog" / "kinds" / "defined"
SKIPPED = frozenset({"__pycache__", "alembic", "migration", "defined"})
CONTENT = frozenset({"authored", "closed"})
ALIAS = re.compile(r"type (\w+) = (?:components\['schemas'\]|Schema)\['(\w+)'\]")
LABEL_ENTRY = re.compile(r"^\s*'?([a-z0-9_]+)'?:\s*(?:\{\s*label:\s*)?(['\"])((?:(?!\2)[^\\]|\\.)*)\2", re.M)
RUFF = ROOT / "backend" / ".venv" / "bin" / "ruff"


@dataclass
class Uses:
    checked: set[str] = field(default_factory=set)
    used: set[str] = field(default_factory=set)


def snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).upper()


def is_read(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> bool:
    child, parent = node, parents.get(node)
    while isinstance(parent, (ast.Tuple, ast.List, ast.Set)):
        child, parent = parent, parents.get(parent)
    if isinstance(parent, (ast.Compare, ast.MatchValue)):
        return True
    return isinstance(parent, ast.Dict) and any(key is child for key in parent.keys)


def place_of(node: ast.AST, parents: dict[ast.AST, ast.AST], module: str) -> str:
    names: list[str] = []
    current: ast.AST | None = node
    top: str | None = None
    while current is not None:
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(current.name)
        if isinstance(current, (ast.Assign, ast.AnnAssign)) and isinstance(parents.get(current), ast.Module):
            targets = current.targets if isinstance(current, ast.Assign) else [current.target]
            top = next((target.id for target in targets if isinstance(target, ast.Name)), None)
        current = parents.get(current)
    where = ".".join(reversed(names)) or top or "module"
    return f"{module.removeprefix('aerona.')}.{where}"


def uses(known: dict[str, list[tuple[str, str]]], wanted: set[str], source: Path = SOURCE) -> dict[tuple[str, str], Uses]:
    found: dict[tuple[str, str], Uses] = {}
    members = {name: {member for member, _ in values} for name, values in known.items()}
    for path in sorted(source.rglob("*.py")):
        if SKIPPED & set(path.relative_to(source).parts) or path.parent.name == "enums":
            continue
        tree = parsed(path)
        aliases = {alias: key for alias, key in enum_aliases(tree, {name: name for name in known}).items() if key in wanted}
        if not aliases:
            continue
        parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
        module = ".".join(path.relative_to(source).with_suffix("").parts)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in aliases:
                key = aliases[node.value.id]
                if node.attr not in members[key]:
                    continue
                entry = found.setdefault((key, node.attr), Uses())
                (entry.checked if is_read(node, parents) else entry.used).add(place_of(node, parents, module))
    return found


def frontend_labels() -> dict[str, dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    for path in sorted(FRONTEND.rglob("*.ts*")):
        if "generated" in path.parts or ".test." in path.name:
            continue
        text = path.read_text(encoding="utf-8")
        aliases = dict(ALIAS.findall(text))
        for match in re.finditer(r"Record<\s*(?:components\['schemas'\]|Schema)\['(\w+)'\]|Record<\s*(\w+)\s*,", text):
            enum = match.group(1) or aliases.get(match.group(2) or "", "")
            if not enum:
                continue
            start = text.find("{", match.end())
            end = text.find("\n}", start)
            if start < 0 or end < 0:
                continue
            labels = found.setdefault(enum, {})
            for key, _, label in LABEL_ENTRY.findall(text[start:end]):
                labels.setdefault(key, label.replace("\\'", "'"))
    return found


def text_of(value: str) -> str:
    value = value.replace("\u2019", "'")
    return repr(value) if '"' in value and "'" not in value else '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def wanted_enums() -> list[str]:
    layers = declared()
    known = all_enums()
    totals = catalogued()
    return sorted(name for name, entry in layers.items() if name in known and entry.layer in CONTENT and name.split(".")[1] not in totals)


def render() -> dict[Path, str]:
    known = all_enums()
    wanted = wanted_enums()
    found = uses(known, set(wanted))
    labels = frontend_labels()
    by_module: dict[str, list[str]] = {}
    for name in wanted:
        by_module.setdefault(name.split(".")[0], []).append(name)
    files: dict[Path, str] = {}
    registry: list[str] = []
    for stem, names in sorted(by_module.items()):
        enums = sorted(name.split(".")[1] for name in names)
        lines = [
            "from aerona.catalog.kinds.definition import Defined",
            "from aerona.core.total import total",
            f"from aerona.domain.enums.{stem} import {', '.join(enums)}",
            "",
        ]
        for name in names:
            enum = name.split(".")[1]
            lines += ["", f"{snake(enum)} = total(", f"    {enum},", "    {"]
            for member, value in known[name]:
                entry = found.get((name, member), Uses())
                label = labels.get(enum, {}).get(value) or value.replace("_", " ").capitalize()
                checked = ", ".join(text_of(item) for item in sorted(entry.checked))
                used = ", ".join(text_of(item) for item in sorted(entry.used))
                checked_by = f"({checked}{',' if len(entry.checked) == 1 else ''})"
                used_by = f"({used}{',' if len(entry.used) == 1 else ''})"
                lines.append(f"        {enum}.{member}: Defined({text_of(label)}, checked_by={checked_by}, used_by={used_by}),")
            lines += ["    },", ")"]
            registry.append(f'    "{name}": {stem}.{snake(enum)},')
        files[DEFINED / f"{stem}.py"] = "\n".join(lines) + "\n"
    stems = sorted(by_module)
    init = ["from collections.abc import Mapping", "from typing import Any", ""]
    init += [f"from aerona.catalog.kinds.defined import {stem}" for stem in stems]
    init += ["from aerona.catalog.kinds.definition import Defined", "", "DEFINITIONS: dict[str, Mapping[Any, Defined]] = {", *registry, "}"]
    files[DEFINED / "__init__.py"] = "\n".join(init) + "\n"
    return formatted(files)


def ruff(arguments: list[str], path: Path, text: str) -> str:
    done = subprocess.run(
        [str(RUFF), *arguments, "--stdin-filename", str(path), "-"], input=text, capture_output=True, text=True, check=False, cwd=ROOT / "backend"
    )
    return done.stdout or text


def formatted(files: dict[Path, str]) -> dict[Path, str]:
    return {path: ruff(["format"], path, ruff(["check", "--fix", "--select", "I"], path, text)) for path, text in files.items()}


def missing() -> list[str]:
    present = registered_definitions()
    return [name for name in wanted_enums() if name not in present]


def stale(files: dict[Path, str]) -> list[Path]:
    current = {path for path in DEFINED.glob("*.py")} if DEFINED.exists() else set()
    changed = [path for path, text in files.items() if not path.exists() or path.read_text(encoding="utf-8") != text]
    return sorted(changed + [path for path in current - set(files)])


def main() -> int:
    files = render()
    if sys.argv[1:] == ["write"]:
        DEFINED.mkdir(parents=True, exist_ok=True)
        for path in set(DEFINED.glob("*.py")) - set(files):
            path.unlink()
        for path, text in files.items():
            path.write_text(text, encoding="utf-8")
        print(f"kind definitions: wrote {len(files)} file(s)")
        return 0
    gaps = missing()
    old = stale(files)
    for name in gaps:
        print(f"{name}: a content enum with no property catalogue")
    for path in old:
        print(f"{path.relative_to(ROOT)}: out of date; run scripts/check_kind_definitions.py write")
    print(f"kind definitions: {len(gaps) + len(old)} problem(s)")
    return 1 if gaps or old else 0


if __name__ == "__main__":
    sys.exit(main())
