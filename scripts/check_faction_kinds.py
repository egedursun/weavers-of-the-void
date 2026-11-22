import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
MAPPING = SOURCE / "domain" / "enums" / "faction.py"
MAPPING_NAME = "KIND_OF_ENGINE"


@dataclass(frozen=True)
class Read:
    path: Path
    line: int
    kind: str


def faction_engine_kinds(text: str) -> frozenset[str]:
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == MAPPING_NAME for target in node.targets):
            return frozenset(
                key.attr
                for item in ast.walk(node.value)
                if isinstance(item, ast.Dict)
                for key in item.keys
                if isinstance(key, ast.Attribute) and isinstance(key.value, ast.Name) and key.value.id == "EngineKind"
            )
    return frozenset()


def named_kinds(node: ast.AST, kinds: frozenset[str]) -> list[str]:
    return [
        item.attr
        for item in ast.walk(node)
        if isinstance(item, ast.Attribute) and isinstance(item.value, ast.Name) and item.value.id == "EngineKind" and item.attr in kinds
    ]


def engine_kind(node: ast.AST) -> bool:
    return isinstance(node, ast.Attribute) and node.attr == "engine_kind"


def reads_in(text: str, kinds: frozenset[str]) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Compare):
            operands = [node.left, *node.comparators]
            if any(engine_kind(item) for item in operands):
                found.extend((node.lineno, kind) for item in operands if not engine_kind(item) for kind in named_kinds(item, kinds))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"in_", "not_in"} and engine_kind(node.func.value):
            found.extend((node.lineno, kind) for argument in node.args for kind in named_kinds(argument, kinds))
    return sorted(found)


def reads(files: dict[Path, str], kinds: frozenset[str]) -> list[Read]:
    return [Read(path, line, kind) for path, text in files.items() for line, kind in reads_in(text, kinds)]


def sources() -> dict[Path, str]:
    return {path: path.read_text(encoding="utf-8") for path in sorted(SOURCE.rglob("*.py")) if path != MAPPING}


def main() -> int:
    kinds = faction_engine_kinds(MAPPING.read_text(encoding="utf-8"))
    if not kinds:
        print(f"faction kinds: {MAPPING_NAME} not found in {MAPPING.relative_to(ROOT)}")
        return 1
    found = reads(sources(), kinds)
    for item in found:
        print(
            f"{item.path.relative_to(ROOT)}:{item.line}: reads a faction's kind through engine_kind ({item.kind}); "
            "the faction's profile holds its kind, which tools and gods change, so read it through of_kinds or kind_of from db/faction_kinds.py"
        )
    print(f"faction kinds: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
