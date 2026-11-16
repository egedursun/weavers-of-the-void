import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
SKIPPED = (SOURCE / "db" / "alembic",)
SENTENCE_WORDS = 4
PHRASE_WORDS = 3
VARIANTS = 3
POOL_SIZE = 2
PICKERS = frozenset({"pick", "choice", "choices", "sample", "weighted"})


@dataclass(frozen=True)
class Pool:
    path: Path
    line: int
    name: str


def is_sentence(item: ast.expr) -> bool:
    if isinstance(item, ast.Constant) and isinstance(item.value, str):
        return len(item.value.split()) >= SENTENCE_WORDS
    return isinstance(item, (ast.Tuple, ast.List)) and bool(item.elts) and all(is_sentence(inner) for inner in item.elts)


def variant_tuple(item: ast.expr) -> bool:
    phrases = (
        [inner for inner in item.elts if isinstance(inner, ast.Constant) and isinstance(inner.value, str)] if isinstance(item, (ast.Tuple, ast.List)) else []
    )
    return len(phrases) >= VARIANTS and len(phrases) == len(item.elts) and all(len(inner.value.split()) >= PHRASE_WORDS for inner in phrases)


def variant_dict(node: ast.expr) -> bool:
    return isinstance(node, ast.Dict) and sum(1 for value in node.values if variant_tuple(value)) >= POOL_SIZE


def sentences(node: ast.expr) -> int:
    if not isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return 0
    prose = sum(1 for item in node.elts if is_sentence(item))
    lines = sum(1 for item in node.elts if isinstance(item, ast.Call) and isinstance(item.func, ast.Name) and item.func.id == "Line")
    return max(prose, lines)


def pools(files: dict[Path, str]) -> list[Pool]:
    found: list[Pool] = []
    for path, text in files.items():
        tree = ast.parse(text)
        for node in tree.body:
            value = node.value if isinstance(node, (ast.Assign, ast.AnnAssign)) else None
            if value is not None and (sentences(value) >= POOL_SIZE or variant_dict(value)):
                target = node.targets[0] if isinstance(node, ast.Assign) else node.target
                found.append(Pool(path, node.lineno, ast.unparse(target)))
        for call in ast.walk(tree):
            picked = isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr in PICKERS
            if picked and any(sentences(argument) >= POOL_SIZE for argument in call.args):
                found.append(Pool(path, call.lineno, ast.unparse(call.func)))
    return found


def sources() -> dict[Path, str]:
    return {
        path: path.read_text(encoding="utf-8")
        for path in sorted(SOURCE.rglob("*.py"))
        if "__pycache__" not in path.parts and not any(path.is_relative_to(base) for base in SKIPPED)
    }


def main() -> int:
    found = pools(sources())
    for item in found:
        print(f"{item.path.relative_to(ROOT)}:{item.line}: {item.name} is a pool of canned sentences; tell the happening once, plainly, from its typed fields")
    print(f"canned lines: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
