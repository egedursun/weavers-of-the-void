import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
CALLS = frozenset({"Harm", "gain_condition"})
FIXED_HARM_KINDS = frozenset({"BITE", "MIND_SCAR"})


def findings() -> list[str]:
    found: list[str] = []
    for path in sorted(SOURCE.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.Call):
                continue
            name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
            if name not in CALLS:
                continue
            for keyword in node.keywords:
                where = f"{path.relative_to(ROOT)}:{node.lineno}"
                if keyword.arg == "severity" and isinstance(keyword.value, ast.Constant):
                    found.append(f"{where}: {name} passes a literal severity; pass a magnitude and let severity_of draw it")
                literal_kind = (
                    isinstance(keyword.value, ast.Attribute) and isinstance(keyword.value.value, ast.Name) and keyword.value.value.id.endswith("Kind")
                )
                if keyword.arg == "kind" and literal_kind and isinstance(keyword.value, ast.Attribute) and keyword.value.attr not in FIXED_HARM_KINDS:
                    found.append(f"{where}: {name} fixes the injury kind {keyword.value.attr}; let kind_for draw it from the damage type")
    return found


def main() -> int:
    found = findings()
    for line in found:
        print(line)
    print(f"fixed harm: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
