import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
CACHES = frozenset({"cache", "lru_cache", "cached"})
OPEN_ENUMS = frozenset({"Enum", "StrEnum", "IntEnum", "Flag", "IntFlag", "ReprEnum"})


@dataclass(frozen=True)
class EnumCache:
    path: Path
    line: int
    function: str
    parameter: str


def decorator_name(node: ast.expr) -> str:
    target = node.func if isinstance(node, ast.Call) else node
    if isinstance(target, ast.Attribute):
        return target.attr
    return target.id if isinstance(target, ast.Name) else ""


def annotation_names(node: ast.expr | None) -> set[str]:
    if node is None:
        return set()
    return {part.id for part in ast.walk(node) if isinstance(part, ast.Name)} | {part.attr for part in ast.walk(node) if isinstance(part, ast.Attribute)}


def enum_caches(path: Path, text: str) -> list[EnumCache]:
    found: list[EnumCache] = []
    for node in ast.walk(ast.parse(text)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or not any(decorator_name(item) in CACHES for item in node.decorator_list):
            continue
        arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
        found.extend(
            EnumCache(path, node.lineno, node.name, argument.arg)
            for argument in arguments
            if annotation_names(argument.annotation) & OPEN_ENUMS and not isinstance(argument.annotation, ast.Subscript)
        )
    return found


def sources() -> dict[Path, str]:
    return {path: path.read_text(encoding="utf-8") for path in sorted(SOURCE.rglob("*.py"))}


def main() -> int:
    found = [item for path, text in sources().items() for item in enum_caches(path, text)]
    for item in found:
        print(
            f"{item.path.relative_to(ROOT)}:{item.line}: {item.function} caches by `{item.parameter}`, an enum of any type; members of two enums "
            "with the same name compare equal and share a key, so one enum's wording answers for the other. Key the cache by the enum's type and value"
        )
    print(f"enum caches: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
