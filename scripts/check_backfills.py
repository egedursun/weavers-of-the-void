import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "backend" / "src" / "aerona" / "engine"


def once_of(tree: ast.Module) -> set[str]:
    return {
        node.name
        for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef)
        and any(
            isinstance(mark, ast.Name) and mark.id == "once"
            for mark in node.decorator_list
        )
    }


def called(function: ast.AST, names: set[str]) -> set[str]:
    return {
        node.func.id
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in names
    }


def lagging_steps(engine: Path = ENGINE) -> list[str]:
    found: list[str] = []
    for path in sorted(engine.glob("*/backfill.py")):
        tree = ast.parse(path.read_text())
        functions = {
            node.name: node
            for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef)
        }
        once = once_of(tree)
        for name, function in functions.items():
            if not name.endswith("backfill"):
                continue
            for step in sorted(called(function, set(functions))):
                kept = any(
                    step in called(other, set(functions))
                    for other_name, other in functions.items()
                    if other_name not in {name, step}
                )
                if not kept and step not in once:
                    found.append(
                        f"{path.relative_to(ROOT)}: {step} runs only in {name}, so things that arrive later never get it; run it each epoch or mark it @once"
                    )
    return found


def main() -> int:
    found = lagging_steps()
    for line in found:
        print(line)
    print(f"backfills that leave later arrivals behind: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
