import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "backend" / "src" / "aerona"
MODEL_FACING = ("agents/context", "prompts/contexts", "tools")
SPACE = re.compile(r"\s")


def raw_values(text: str) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(text)):
        if not isinstance(node, ast.JoinedStr):
            continue
        literal = "".join(str(part.value) for part in node.values if isinstance(part, ast.Constant))
        if not SPACE.search(literal):
            continue
        for part in node.values:
            if isinstance(part, ast.FormattedValue) and part.conversion == -1 and part.format_spec is None:
                value = part.value
                if isinstance(value, ast.Attribute) and value.attr == "value":
                    found.append((node.lineno, ast.unparse(value.value)))
    return found


def main() -> int:
    found = 0
    for folder in MODEL_FACING:
        for path in sorted((PACKAGE / folder).rglob("*.py")):
            for line_number, name in raw_values(path.read_text(encoding="utf-8")):
                print(f"{path.relative_to(ROOT)}:{line_number}: {name}.value reaches the model as a raw key; write it through spoken()")
                found += 1
    print(f"model enum text: {found}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
