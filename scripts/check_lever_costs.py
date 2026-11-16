import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "backend" / "src" / "aerona"
CATALOG = PACKAGE / "services" / "player" / "catalog.py"
PLAYER = PACKAGE / "services" / "player"
CHARGES = frozenset({"charge", "spend", "spend_essence", "pay_essence"})


def charging_functions(folder: Path = PLAYER) -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for path in folder.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
                continue
            for call in ast.walk(node):
                if isinstance(call, ast.Call):
                    name = call.func.attr if isinstance(call.func, ast.Attribute) else call.func.id if isinstance(call.func, ast.Name) else ""
                    if name in CHARGES:
                        found.add((path.stem, node.name))
                        break
    return found


def free_levers(catalog: Path = CATALOG) -> list[tuple[str, str, str]]:
    tree = ast.parse(catalog.read_text(encoding="utf-8"))
    levers: list[tuple[str, str, str]] = []
    for call in ast.walk(tree):
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id in {"_sync", "_job"} and len(call.args) >= 4):
            continue
        meta, handler, cost = call.args[0], call.args[1], call.args[3]
        if not (isinstance(cost, ast.Name) and cost.id == "free" and isinstance(handler, ast.Attribute) and isinstance(handler.value, ast.Name)):
            continue
        action = meta.args[0].value if isinstance(meta, ast.Call) and meta.args and isinstance(meta.args[0], ast.Constant) else "?"
        levers.append((str(action), handler.value.id, handler.attr))
    return levers


def mispriced(folder: Path = PLAYER, catalog: Path = CATALOG) -> list[tuple[str, str, str]]:
    charging = charging_functions(folder)
    return [lever for lever in free_levers(catalog) if (lever[1], lever[2]) in charging]


def main() -> int:
    wrong = mispriced()
    for action, module, function in wrong:
        print(f"{action}: {module}.{function} charges essence but the catalog calls it free; give it the cost its rule sets")
    print(f"lever costs: {len(wrong)}")
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main())
