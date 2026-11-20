import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
STREAM_CALLS = frozenset({"rng", "child"})


@dataclass(frozen=True)
class LooseKey:
    path: Path
    line: int
    name: str
    text: str


def optional(annotation: ast.expr | None) -> bool:
    if annotation is None:
        return False
    text = ast.unparse(annotation)
    return "None" in text or text.startswith("Optional")


def optional_names(function: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    names = {item.arg for item in [*function.args.posonlyargs, *function.args.args, *function.args.kwonlyargs] if optional(item.annotation)}
    for node in ast.walk(function):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and optional(node.annotation):
            names.add(node.target.id)
    return names


def checked(function: ast.FunctionDef | ast.AsyncFunctionDef, name: str, before: int) -> bool:
    for node in ast.walk(function):
        if getattr(node, "lineno", before + 1) > before:
            continue
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Name) and node.left.id == name:
            if any(isinstance(op, (ast.Is, ast.IsNot)) for op in node.ops) and any(isinstance(item, ast.Constant) and item.value is None for item in node.comparators):
                return True
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not) and isinstance(node.operand, ast.Name) and node.operand.id == name:
            return True
    return False


def keyed_by(call: ast.Call) -> list[ast.Name]:
    if not (isinstance(call.func, ast.Attribute) and call.func.attr in STREAM_CALLS and call.args and isinstance(call.args[0], ast.JoinedStr)):
        return []
    return [part.value for part in call.args[0].values if isinstance(part, ast.FormattedValue) and isinstance(part.value, ast.Name)]


def loose_keys(files: dict[Path, str]) -> list[LooseKey]:
    found: list[LooseKey] = []
    for path, text in files.items():
        for function in ast.walk(ast.parse(text)):
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            names = optional_names(function)
            if not names:
                continue
            for call in ast.walk(function):
                if not isinstance(call, ast.Call):
                    continue
                for value in keyed_by(call):
                    if value.id in names and not checked(function, value.id, call.lineno):
                        found.append(LooseKey(path, call.lineno, value.id, ast.unparse(call.args[0])))
    return found


def main() -> int:
    found = loose_keys({path: path.read_text(encoding="utf-8") for path in sorted(SOURCE.rglob("*.py"))})
    for item in found:
        print(f"{item.path.relative_to(ROOT)}:{item.line}: the random stream {item.text} is keyed by {item.name}, which may be None; key a missing value by a word")
    print(f"loose stream keys: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
