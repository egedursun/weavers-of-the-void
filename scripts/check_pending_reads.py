import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROUTERS = ROOT / "backend" / "src" / "aerona" / "api" / "routers"
REFUSALS = {"NotFoundError", "ValidationFailedError"}
NOT_YET = re.compile(r"\byet\b|next epoch|not been surveyed|surveyed at|not been studied|forms on", re.I)


def reads(tree: ast.Module) -> list[ast.AsyncFunctionDef | ast.FunctionDef]:
    found: list[ast.AsyncFunctionDef | ast.FunctionDef] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            for decorator in node.decorator_list:
                if not (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute) and decorator.func.attr == "get"):
                    continue
                if any(keyword.arg == "response_class" for keyword in decorator.keywords):
                    continue
                found.append(node)
    return found


def constants(tree: ast.Module) -> dict[str, str]:
    named: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    named[target.id] = node.value.value
    return named


def message(argument: ast.expr, named: dict[str, str]) -> str:
    if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
        return argument.value
    if isinstance(argument, ast.Name):
        return named.get(argument.id, "")
    if isinstance(argument, ast.JoinedStr):
        return "".join(part.value for part in argument.values if isinstance(part, ast.Constant) and isinstance(part.value, str))
    return ""


def pending_refusals(source: str) -> list[tuple[str, int, str]]:
    tree = ast.parse(source)
    named = constants(tree)
    found: list[tuple[str, int, str]] = []
    for function in reads(tree):
        for node in ast.walk(function):
            if not (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name)):
                continue
            if node.exc.func.id not in REFUSALS or not node.exc.args:
                continue
            text = message(node.exc.args[0], named)
            if NOT_YET.search(text):
                found.append((function.name, node.lineno, text))
    return found


def main() -> int:
    problems = [
        f"{path.relative_to(ROOT)}:{line} {name} refuses with '{text}'"
        for path in sorted(ROUTERS.rglob("*.py"))
        for name, line, text in pending_refusals(path.read_text(encoding="utf-8"))
    ]
    for problem in problems:
        print(f"{problem}. A record that is not made yet is a normal state: answer null and let the screen say so, not an error.")
    print(f"pending reads: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
