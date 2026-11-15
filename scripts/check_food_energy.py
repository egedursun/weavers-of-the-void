import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona" / "engine" / "economy"
FOOD_WORDS = ("harvest", "farm", "fish", "gather", "forage")
POOLED_DRAW = "scale_by_energy"


@dataclass(frozen=True)
class PooledFood:
    path: Path
    line: int
    function: str


def pooled_food(files: dict[Path, str]) -> list[PooledFood]:
    found: list[PooledFood] = []
    for path, text in files.items():
        for function in ast.walk(ast.parse(text)):
            if not isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef) or not any(word in function.name for word in FOOD_WORDS):
                continue
            for node in ast.walk(function):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == POOLED_DRAW:
                    found.append(PooledFood(path, node.lineno, function.name))
    return found


def main() -> int:
    found = pooled_food({path: path.read_text(encoding="utf-8") for path in sorted(SOURCE.rglob("*.py"))})
    for item in found:
        where = f"{item.path.relative_to(ROOT)}:{item.line}"
        print(f"{where}: {item.function} feeds the town from the shared pool of energy only; its own workers work first, use worked_by_hand")
    print(f"food drawn only from the shared pool: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
