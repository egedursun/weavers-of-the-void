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
TREASURY = "treasury"
POINT_STATS = frozenset({"wealth", "prosperity"})
POINT_WRITERS = frozenset({"add_prosperity"})
CONVERTERS = frozenset({"wealth_points", "take_coin", "give_coin", "receive_coin", "coin_of", "wealth_per_treasury"})
BLOCKS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try)


@dataclass(frozen=True)
class Mixed:
    path: Path
    line: int
    field: str


def rules_of(texts: list[str]) -> list[tuple[str, str]]:
    return [(name, text) for source in texts for name, text in RULE.findall(source)]


def treasury_fields(texts: list[str]) -> frozenset[str]:
    rules = rules_of(texts)
    treasury = {name for name, text in rules if text.startswith("Treasury") and "wealth" not in text}
    other = {name for name, text in rules if not text.startswith("Treasury")}
    return frozenset(treasury - other)


def bridge_fields(texts: list[str]) -> frozenset[str]:
    return frozenset(name for name, text in rules_of(texts) if text.startswith("Treasury") and "wealth" in text)


def touches_wealth(node: ast.AST) -> bool:
    return any(
        (isinstance(item, ast.Constant) and item.value in POINT_STATS) or (isinstance(item, ast.Name) and item.id in POINT_WRITERS) for item in ast.walk(node)
    )


def names_in(node: ast.AST) -> set[str]:
    return {item.attr for item in ast.walk(node) if isinstance(item, ast.Attribute)} | {item.id for item in ast.walk(node) if isinstance(item, ast.Name)}


def treasury_names(function: ast.AST, coins: frozenset[str], converters: frozenset[str]) -> frozenset[str]:
    names: set[str] = set()
    for node in ast.walk(function):
        if isinstance(node, ast.Assign) and any(coin_named(name, coins) for name in names_in(node.value)) and not names_in(node.value) & converters:
            names.update(target.id for target in node.targets if isinstance(target, ast.Name))
    return frozenset(names)


def coin_named(name: str, coins: frozenset[str]) -> bool:
    return name in coins or (TREASURY in name and name not in CONVERTERS)


def coin_in(node: ast.AST, coins: frozenset[str], derived: frozenset[str]) -> set[str]:
    attributes = {item.attr for item in ast.walk(node) if isinstance(item, ast.Attribute) and coin_named(item.attr, coins)}
    return attributes | ({item.id for item in ast.walk(node) if isinstance(item, ast.Name)} & derived)


def meeting(node: ast.AST, coins: frozenset[str], derived: frozenset[str]) -> set[str]:
    found = coin_in(node, coins, derived)
    if not found or not touches_wealth(node):
        return set()
    if isinstance(node, ast.Call):
        keyed = set().union(*(meeting(keyword.value, coins, derived) for keyword in node.keywords))
        positional: list[ast.AST] = [node.func, *node.args]
        both = [part for part in positional if touches_wealth(part) and coin_in(part, coins, derived)]
        if both:
            return keyed.union(*(meeting(part, coins, derived) for part in both))
        crossed = any(touches_wealth(part) for part in positional)
        return keyed | (set().union(*(coin_in(part, coins, derived) for part in positional)) if crossed else set())
    holders = [child for child in ast.iter_child_nodes(node) if touches_wealth(child) and coin_in(child, coins, derived)]
    return set().union(*(meeting(child, coins, derived) for child in holders)) if holders else found


def mixed_units(files: dict[Path, str], fields: frozenset[str], bridges: frozenset[str] = frozenset()) -> list[Mixed]:
    coins = fields | {TREASURY}
    converters = CONVERTERS | bridges
    found: set[Mixed] = set()
    for path, text in files.items():
        for function in ast.walk(ast.parse(text)):
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            derived = treasury_names(function, coins, converters)
            for statement in ast.walk(function):
                if not isinstance(statement, ast.stmt) or isinstance(statement, BLOCKS) or names_in(statement) & converters:
                    continue
                found.update(Mixed(path, statement.lineno, field) for field in sorted(meeting(statement, coins, derived)))
    return sorted(found, key=lambda item: (str(item.path), item.line, item.field))


def main() -> int:
    texts = [path.read_text(encoding="utf-8") for path in sorted(RULES.rglob("*.py"))]
    found = mixed_units({path: path.read_text(encoding="utf-8") for path in sorted(ENGINE.rglob("*.py"))}, treasury_fields(texts), bridge_fields(texts))
    for item in found:
        print(f"{item.path.relative_to(ROOT)}:{item.line}: {item.field} is treasury but meets wealth points unconverted; use engine/economy/purse.py")
    print(f"mixed coin units: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
