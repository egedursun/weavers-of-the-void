import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROUTERS = ROOT / "backend" / "src" / "aerona" / "api" / "routers"
OFFSET_SLICE = re.compile(r"\[\s*(\w*offset)\s*:\s*\1\s*\+")
MEMO = "per_state("


def handlers(path: Path) -> list[tuple[str, str, int]]:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    return [
        (node.name, ast.get_source_segment(text, node) or "", node.lineno)
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef)
        and any(
            isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute) and decorator.func.attr == "get" for decorator in node.decorator_list
        )
    ]


def rebuilt_pages(source: str) -> bool:
    return OFFSET_SLICE.search(source) is not None and MEMO not in source


def main() -> int:
    problems = [
        f"{path.relative_to(ROOT)}:{line} {name}" for path in sorted(ROUTERS.glob("*.py")) for name, source, line in handlers(path) if rebuilt_pages(source)
    ]
    for problem in problems:
        print(
            f"{problem} pages a list it builds again for every page, so a screen that reads every page builds it once per page."
            " Build it once per world state with per_state from services/state_memo.py and slice that."
        )
    print(f"paged reads: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
