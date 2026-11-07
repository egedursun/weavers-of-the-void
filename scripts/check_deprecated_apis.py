import ast
import importlib
import inspect
import sys
import warnings
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parent.parent
SCANNED = (ROOT / "backend" / "src", ROOT / "backend" / "tests", ROOT / "scripts")
LIBRARY_MODULES = (
    "sqlalchemy",
    "sqlalchemy.orm",
    "sqlalchemy.engine",
    "sqlalchemy.engine.result",
    "sqlalchemy.ext.asyncio",
    "sqlalchemy.ext.asyncio.result",
    "sqlalchemy.sql",
    "sqlalchemy.sql.expression",
    "sqlalchemy.schema",
    "pydantic",
    "pydantic.main",
    "fastapi",
    "starlette.requests",
    "starlette.responses",
    "httpx",
    "alembic.op",
)
DEPRECATION_MARKERS = (".. deprecated::",)


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    name: str
    owners: tuple[str, ...]


def loaded(name: str) -> ModuleType | None:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return importlib.import_module(name)
    except ImportError:
        return None


def deprecated(member: object) -> bool:
    if getattr(member, "__deprecated__", None) is not None or getattr(member, "_sa_warn", None) is not None:
        return True
    target = member.fget if isinstance(member, property) and member.fget is not None else member
    lines = inspect.cleandoc(getattr(target, "__doc__", None) or "").lower().splitlines()
    return any(line.startswith(marker) for line in lines for marker in DEPRECATION_MARKERS)


def library_members() -> tuple[dict[str, set[str]], set[str]]:
    retired: dict[str, set[str]] = defaultdict(set)
    current: set[str] = set()
    for module_name in LIBRARY_MODULES:
        module = loaded(module_name)
        if module is None:
            continue
        for owner_name, owner in vars(module).items():
            if owner_name.startswith("_"):
                continue
            if inspect.isclass(owner):
                for name in dir(owner):
                    if name.startswith("_"):
                        continue
                    member = inspect.getattr_static(owner, name, None)
                    (retired[name].add(f"{owner.__module__}.{owner.__qualname__}") if deprecated(member) else current.add(name))
            elif callable(owner):
                (retired[owner_name].add(module_name) if deprecated(owner) else current.add(owner_name))
    return retired, current


def own_names(paths: list[Path]) -> set[str]:
    names: set[str] = set()
    for path in paths:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        names.add(item.name)
                    elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        names.add(item.target.id)
                    elif isinstance(item, ast.Assign):
                        names.update(target.id for target in item.targets if isinstance(target, ast.Name))
            elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
                names.add(node.attr)
    return names


def unambiguous(retired: dict[str, set[str]], current: set[str], own: set[str]) -> dict[str, tuple[str, ...]]:
    return {name: tuple(sorted(owners)) for name, owners in retired.items() if name not in current and name not in own}


def sources() -> list[Path]:
    found: list[Path] = []
    for root in SCANNED:
        found.extend(path for path in sorted(root.rglob("*.py")) if "__pycache__" not in path.parts and ".venv" not in path.parts)
    return found


def scan(path: Path, banned: dict[str, tuple[str, ...]]) -> list[Finding]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in banned:
            findings.append(Finding(path, node.lineno, node.attr, banned[node.attr]))
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] in {"sqlalchemy", "pydantic", "fastapi", "httpx"}:
            findings.extend(Finding(path, node.lineno, alias.name, banned[alias.name]) for alias in node.names if alias.name in banned)
    return findings


def main() -> int:
    retired, current = library_members()
    paths = sources()
    banned = unambiguous(retired, current, own_names(paths))
    findings = [finding for path in paths for finding in scan(path, banned)]
    for finding in findings:
        print(f"{finding.path.relative_to(ROOT)}:{finding.line}: deprecated library API '{finding.name}' ({', '.join(finding.owners[:3])})")
    if findings:
        print(f"{len(findings)} use(s) of deprecated library APIs; use the current API instead.")
        return 1
    print(f"deprecated APIs: 0 uses of {len(banned)} retired names")
    return 0


if __name__ == "__main__":
    sys.exit(main())
