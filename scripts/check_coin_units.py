import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
RULES = SOURCE / "rules" / "registry"
ENGINE = SOURCE / "engine"
RULE = re.compile(r"^\s+(\w+): int = rule\([^\n]*\"([^\"]*)\"\)", re.M)
CONVERTERS = frozenset({"wealth_points", "take_coin", "give_coin", "coin_of", "wealth_per_treasury"})
BLOCKS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try)


@dataclass(frozen=True)
class Mixed:
    path: Path
    line: int
    field: str


def treasury_fields(texts: list[str]) -> frozenset[str]:
    rules = [(name, text) for source in texts for name, text in RULE.findall(source)]
    treasury = {name for name, text in rules if text.startswith("Treasury") and "wealth" not in text}
    other = {name for name, text in rules if not text.startswith("Treasury")}
    return frozenset(treasury - other)


def touches_wealth(node: ast.AST) -> bool:
    return any(isinstance(item, ast.Constant) and item.value == "wealth" for item in ast.walk(node))


def mixed_units(files: dict[Path, str], fields: frozenset[str]) -> list[Mixed]:
    found: list[Mixed] = []
    for path, text in files.items():
        for statement in ast.walk(ast.parse(text)):
            if not isinstance(statement, ast.stmt) or isinstance(statement, BLOCKS) or not touches_wealth(statement):
                continue
            attributes = {node.attr for node in ast.walk(statement) if isinstance(node, ast.Attribute)}
            called = {node.id for node in ast.walk(statement) if isinstance(node, ast.Name)}
            if (attributes | called) & CONVERTERS:
                continue
            found.extend(Mixed(path, statement.lineno, field) for field in sorted(attributes & fields))
    return found


def main() -> int:
    fields = treasury_fields([path.read_text(encoding="utf-8") for path in sorted(RULES.rglob("*.py"))])
    found = mixed_units({path: path.read_text(encoding="utf-8") for path in sorted(ENGINE.rglob("*.py"))}, fields)
    for item in found:
        print(f"{item.path.relative_to(ROOT)}:{item.line}: {item.field} is treasury but meets wealth points unconverted; use engine/economy/purse.py")
    print(f"mixed coin units: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
