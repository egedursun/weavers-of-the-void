import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"
EXEMPT = frozenset({"db/tables/economy.py"})


def makers(tree: ast.AST) -> list[ast.AsyncFunctionDef | ast.FunctionDef]:
    found: list[ast.AsyncFunctionDef | ast.FunctionDef] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            built = any(isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "CurrencyRow" for call in ast.walk(node))
            if built:
                found.append(node)
    return found


def establishes(function: ast.AsyncFunctionDef | ast.FunctionDef) -> bool:
    return any(isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "establish" for call in ast.walk(function))


def test_every_currency_the_engine_or_a_god_makes_gets_its_monetary_authority() -> None:
    missing = [
        f"{path.relative_to(SOURCE)}:{function.name}"
        for path in sorted(SOURCE.rglob("*.py"))
        if str(path.relative_to(SOURCE)) not in EXEMPT and "alembic" not in path.parts
        for function in makers(ast.parse(path.read_text()))
        if not establishes(function)
    ]
    assert not missing, f"these make a currency without its monetary authority; call establish() from engine/monetary/authorities.py: {missing}"
