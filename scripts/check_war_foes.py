import ast
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
HOME = SOURCE / "engine" / "services" / "war.py"


@dataclass(frozen=True)
class Raw:
    path: Path
    line: int
    text: str


def side_field(node: ast.AST, name: str) -> bool:
    return isinstance(node, ast.Attribute) and node.attr == name


def ternary_foes(tree: ast.AST) -> Iterator[ast.AST]:
    for node in ast.walk(tree):
        if not isinstance(node, ast.IfExp) or not isinstance(node.test, ast.Compare):
            continue
        fields = {item.attr for item in (node.body, node.orelse, node.test.left, *node.test.comparators) if isinstance(item, ast.Attribute)}
        if {"attacker_id", "defender_id"} <= fields:
            yield node


def filtered_sides(tree: ast.AST) -> Iterator[ast.AST]:
    for node in ast.walk(tree):
        if not isinstance(node, (ast.SetComp, ast.ListComp, ast.GeneratorExp)):
            continue
        for generator in node.generators:
            if side_field(generator.iter, "sides") and any(isinstance(test, ast.Compare) and isinstance(test.ops[0], ast.NotEq) for test in generator.ifs):
                yield node


def raw_foes(files: dict[Path, str]) -> list[Raw]:
    found: set[Raw] = set()
    for path, text in files.items():
        if path == HOME:
            continue
        tree = ast.parse(text)
        found |= {Raw(path, node.lineno, ast.unparse(node)) for node in (*ternary_foes(tree), *filtered_sides(tree))}
    return sorted(found, key=lambda item: (str(item.path), item.line))


def main() -> int:
    found = raw_foes({path: path.read_text(encoding="utf-8") for path in sorted(SOURCE.rglob("*.py"))})
    for item in found:
        print(
            f"{item.path.relative_to(ROOT)}:{item.line}: {item.text} finds a foe by comparing a raw side; a war is fought by peoples, towns and "
            "factions on behalf of realms, use foe_id, foe_of or foe_realms"
        )
    print(f"raw war foes: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
