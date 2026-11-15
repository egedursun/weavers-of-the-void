import ast
import re
import sys
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
SOURCE = BACKEND / "src" / "aerona"
SKIPPED_PARTS = frozenset({".venv", "alembic", "__pycache__"})
READ_SUFFIXES = (".py", ".j2")
FRAMEWORK_BASES = ("TypeDecorator", "BaseModel", "ApiModel", "ToolInput", "Command", "NodeVisitor", "Protocol", "RawIOBase")
FRAMEWORK_DECORATORS = ("validator", "validates", "listens_for", "router", "override", "serializer")
WORD = re.compile(r"\w+")


@dataclass(frozen=True)
class Unused:
    path: Path
    line: int
    name: str


def readable(path: Path) -> bool:
    return path.suffix in READ_SUFFIXES and not SKIPPED_PARTS & set(path.parts)


def base_name(base: ast.expr) -> str:
    return ast.unparse(base.value if isinstance(base, ast.Subscript) else base)


def methods(tree: ast.AST) -> Iterator[tuple[ast.ClassDef, ast.FunctionDef | ast.AsyncFunctionDef]]:
    for cls in ast.walk(tree):
        if not isinstance(cls, ast.ClassDef) or any(base_name(base).endswith(FRAMEWORK_BASES) for base in cls.bases):
            continue
        for item in cls.body:
            if not isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef) or item.name.startswith("__"):
                continue
            if any(mark in ast.unparse(decorator) for decorator in item.decorator_list for mark in FRAMEWORK_DECORATORS):
                continue
            yield cls, item


def unused_methods(sources: dict[Path, str], readers: dict[Path, str]) -> list[Unused]:
    counts = Counter(word for text in readers.values() for word in WORD.findall(text))
    return [
        Unused(path, item.lineno, f"{cls.name}.{item.name}")
        for path, text in sources.items()
        for cls, item in methods(ast.parse(text))
        if counts[item.name] <= 1
    ]


def main() -> int:
    sources = {path: path.read_text(encoding="utf-8") for path in sorted(SOURCE.rglob("*.py")) if readable(path)}
    readers = {path: path.read_text(encoding="utf-8") for path in sorted(BACKEND.rglob("*")) if path.is_file() and readable(path)}
    found = unused_methods(sources, readers)
    for item in found:
        print(f"{item.path.relative_to(ROOT)}:{item.line}: {item.name} is never called; wire it in or delete it")
    print(f"unused methods: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
