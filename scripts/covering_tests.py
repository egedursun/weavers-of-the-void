import ast
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
SOURCE = BACKEND / "src"
TESTS = BACKEND / "tests"
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", re.MULTILINE)
WHOLE_MODULE = "*"


def staged_names() -> list[str]:
    return subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()


def staged_files() -> list[Path]:
    return [ROOT / name for name in staged_names() if name.endswith(".py")]


def readers_of(data: Path) -> dict[str, set[str]]:
    return {
        module_name(path, SOURCE): {WHOLE_MODULE} for path in sorted(SOURCE.rglob("*.py")) if path.is_file() and data.name in path.read_text(encoding="utf-8")
    }


def changed_lines(path: Path) -> set[int]:
    diff = subprocess.run(["git", "diff", "--cached", "-U0", "--", str(path)], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    lines: set[int] = set()
    for match in HUNK.finditer(diff):
        start, count = int(match.group(1)), int(match.group(2) or "1")
        lines.update(range(start, start + max(count, 1)))
    return lines


def module_name(path: Path, base: Path) -> str:
    return ".".join(path.relative_to(base).with_suffix("").parts).removesuffix(".__init__")


def changed_symbols(path: Path) -> set[str]:
    lines = changed_lines(path)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    symbols: set[str] = set()
    for node in tree.body:
        span = set(range(node.lineno, (node.end_lineno or node.lineno) + 1))
        if not span & lines:
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            symbols.update(target.id for target in targets if isinstance(target, ast.Name))
        else:
            symbols.add(WHOLE_MODULE)
    return symbols


def imports_of(path: Path) -> list[tuple[str, set[str]]]:
    found: list[tuple[str, set[str]]] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module:
            found.append((node.module, {alias.name for alias in node.names}))
        elif isinstance(node, ast.Import):
            found.extend((alias.name, {WHOLE_MODULE}) for alias in node.names)
    return found


def covering(changes: dict[str, set[str]]) -> set[Path]:
    chosen: set[Path] = set()
    for test in sorted(path for path in TESTS.rglob("test_*.py") if path.is_file()):
        for module, names in imports_of(test):
            symbols = changes.get(module)
            if symbols is None:
                continue
            if WHOLE_MODULE in symbols or WHOLE_MODULE in names or symbols & names:
                chosen.add(test)
                break
    return chosen


def main() -> int:
    changes: dict[str, set[str]] = {}
    chosen: set[Path] = set()
    for path in staged_files():
        if not path.exists():
            continue
        if path.is_relative_to(SOURCE):
            symbols = changed_symbols(path)
            if symbols:
                changes[module_name(path, SOURCE)] = symbols
        elif path.is_relative_to(TESTS):
            if path.name.startswith("test_"):
                chosen.add(path)
            else:
                changes[module_name(path, BACKEND)] = changed_symbols(path) or {WHOLE_MODULE}
    for name in staged_names():
        data = ROOT / name
        if data.suffix != ".py" and data.is_file() and data.is_relative_to(SOURCE):
            changes.update(readers_of(data))
    chosen |= covering(changes)
    for test in sorted(chosen):
        print(test.relative_to(BACKEND))
    return 0


if __name__ == "__main__":
    sys.exit(main())
