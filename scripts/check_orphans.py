import ast
import io
import re
import sys
import tokenize
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
USERS = (ROOT / "backend" / "tests", ROOT / "scripts", *sorted(path for path in SOURCE.rglob("alembic") if path.is_dir()))
SKIPPED = frozenset({"alembic"})
DEFINITION = re.compile(r"^(?:async )?def ([a-zA-Z]\w*)\(|^([A-Z][A-Z0-9_]+)\s*(?::[^=\n]+)?=", re.M)
WORD = re.compile(r"\b\w+\b")
TEMPLATE_ATTRIBUTE = re.compile(r"\.([a-zA-Z_]\w*)")


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


def names_in(text: str) -> list[str]:
    try:
        return [token.string for token in tokenize.generate_tokens(io.StringIO(text).readline) if token.type == tokenize.NAME]
    except (tokenize.TokenError, SyntaxError):
        return WORD.findall(text)


def orphans(files: dict[Path, str], elsewhere: str) -> list[Orphan]:
    used = Counter(name for text in files.values() for name in names_in(text)) + Counter(names_in(elsewhere))
    found: list[Orphan] = []
    for path, text in files.items():
        for match in DEFINITION.finditer(text):
            name = match.group(1) or match.group(2)
            if used[name] <= 1 and not decorated(text, match.start()):
                found.append(Orphan(path, text.count("\n", 0, match.start()) + 1, name))
    return found


def module_of(path: Path) -> str:
    parts = path.relative_to(SOURCE.parent).with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def references(files: dict[Path, str], users: dict[Path, str]) -> set[tuple[str, str]]:
    modules = {module_of(path) for path in files}
    used: set[tuple[str, str]] = set()
    for path, text in {**files, **users}.items():
        tree = ast.parse(text)
        own = module_of(path) if path in files else None
        bound: dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    used.add((node.module, alias.name))
                    if f"{node.module}.{alias.name}" in modules:
                        bound[alias.asname or alias.name] = f"{node.module}.{alias.name}"
            elif isinstance(node, ast.Import):
                bound.update({alias.asname: alias.name for alias in node.names if alias.asname})
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                base = ast.unparse(node.value)
                if bound.get(base, base) in modules:
                    used.add((bound.get(base, base), node.attr))
            elif own is not None and isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                used.add((own, node.id))
            elif own is not None and isinstance(node, ast.Constant) and isinstance(node.value, str):
                used.add((own, node.value))
    return used


def constants(node: ast.stmt) -> list[str]:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
    names = [item for target in targets for item in (target.elts if isinstance(target, ast.Tuple) else [target])]
    return [item.id for item in names if isinstance(item, ast.Name) and item.id.isupper() and item.id != "__all__"]


def unreferenced(files: dict[Path, str], users: dict[Path, str]) -> list[Orphan]:
    used = references(files, users)
    found: list[Orphan] = []
    for path, text in files.items():
        module = module_of(path)
        for node in ast.parse(text).body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and not node.decorator_list and (module, node.name) not in used:
                found.append(Orphan(path, node.lineno, node.name))
            found.extend(Orphan(path, node.lineno, name) for name in constants(node) if (module, name) not in used)
    return found


def attribute_names(texts: list[str]) -> set[str]:
    names: set[str] = set()
    for text in texts:
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.Attribute):
                names.add(node.attr)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                names.add(node.value)
    return names


def template_names() -> set[str]:
    return {name for path in sorted(SOURCE.rglob("*.j2")) for name in TEMPLATE_ATTRIBUTE.findall(path.read_text(encoding="utf-8"))}


def idle_methods(files: dict[Path, str], users: dict[Path, str]) -> list[Orphan]:
    called = attribute_names([*files.values(), *users.values()]) | template_names()
    found: list[Orphan] = []
    for path, text in files.items():
        for node in ast.walk(ast.parse(text)):
            if not isinstance(node, ast.ClassDef) or node.bases:
                continue
            local = (
                attribute_names([text])
                if any(item.name.startswith("_") for item in node.body if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef))
                else set()
            )
            for method in node.body:
                if not isinstance(method, ast.FunctionDef | ast.AsyncFunctionDef) or method.name.startswith("__"):
                    continue
                if method.name not in (local if method.name.startswith("_") else called):
                    found.append(Orphan(path, method.lineno, f"{node.name}.{method.name}"))
    return found


def main() -> int:
    elsewhere = "\n".join(path.read_text(encoding="utf-8") for folder in USERS for path in sorted(folder.rglob("*.py")) if path.name != Path(__file__).name)
    files = sources()
    users = {path: path.read_text(encoding="utf-8") for folder in USERS for path in sorted(folder.rglob("*.py")) if path.name != Path(__file__).name}
    found = orphans(files, elsewhere)
    seen = {(item.path, item.name) for item in found}
    found += [item for item in unreferenced(files, users) if (item.path, item.name) not in seen]
    found += idle_methods(files, users)
    for item in found:
        print(f"{item.path.relative_to(ROOT)}:{item.line}: {item.name} is defined but never used; wire it or delete it")
    print(f"orphans: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
