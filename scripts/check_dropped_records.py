import ast
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
ENGINE = SOURCE / "engine"
RECORD_API = ENGINE / "recording"
NAMES = frozenset({"log", "lines", "events", "steps"})
RECORD_CALLS = frozenset({"record", "write_steps", "StepDraft"})
RECORD_KEYWORDS = frozenset({"steps"})
FILLERS = frozenset({"append", "extend", "insert"})
CONTAINERS = frozenset({"list", "tuple", "Sequence", "MutableSequence"})
NARRATIVE = frozenset({"str", "dict", "Mapping"})
STEP_LIKE = ("Event", "Step", "Exchange", "Log", "Round", "Blow")


@dataclass(frozen=True)
class Dropped:
    path: Path
    line: int
    reason: str


def call_name(node: ast.Call) -> str:
    func = node.func
    return func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""


def recorded_names(call: ast.Call) -> set[str]:
    named = call_name(call) in RECORD_CALLS
    found: set[str] = set()
    values = (
        [
            *call.args,
            *(keyword.value for keyword in call.keywords if named or keyword.arg in RECORD_KEYWORDS),
        ]
        if named
        else [keyword.value for keyword in call.keywords if keyword.arg in RECORD_KEYWORDS]
    )
    for value in values:
        for inner in ast.walk(value):
            if isinstance(inner, ast.Attribute) and inner.attr in NAMES:
                found.add(f".{inner.attr}")
            if isinstance(inner, ast.Name) and inner.id in NAMES:
                found.add(inner.id)
    return found


def narrative_name(name: str) -> bool:
    return name in NARRATIVE or (name.endswith(STEP_LIKE) and not name.endswith("Row"))


def narrative_annotation(annotation: ast.expr) -> bool:
    if not isinstance(annotation, ast.Subscript) or not isinstance(annotation.value, ast.Name) or annotation.value.id not in CONTAINERS:
        return False
    inner = annotation.slice.elts[0] if isinstance(annotation.slice, ast.Tuple) else annotation.slice
    base = inner.value if isinstance(inner, ast.Subscript) else inner
    return isinstance(base, ast.Name) and narrative_name(base.id)


def narrative_value(node: ast.expr) -> bool:
    if isinstance(node, ast.JoinedStr) or (isinstance(node, ast.Constant) and isinstance(node.value, str)):
        return True
    return isinstance(node, ast.Call) and narrative_name(call_name(node))


def declared_fields(tree: ast.Module) -> list[tuple[str, str, int]]:
    found: list[tuple[str, str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name) and item.target.id in NAMES and narrative_annotation(item.annotation):
                    found.append((node.name, item.target.id, item.lineno))
    return found


def fills(tree: ast.Module, classes: set[str]) -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in FILLERS and isinstance(func.value, ast.Attribute) and func.value.attr in NAMES:
                found.add(("*", func.value.attr))
            if call_name(node) in classes:
                found.update((call_name(node), keyword.arg) for keyword in node.keywords if keyword.arg in NAMES)
                if node.args:
                    found.add((call_name(node), "*positional"))
        if isinstance(node, ast.AugAssign | ast.Assign):
            targets = [node.target] if isinstance(node, ast.AugAssign) else node.targets
            found.update(("*", target.attr) for target in targets if isinstance(target, ast.Attribute) and target.attr in NAMES)
    return found


def narrative_list(node: ast.expr) -> bool:
    if isinstance(node, ast.List):
        return any(narrative_value(item.value if isinstance(item, ast.Starred) else item) for item in node.elts)
    return isinstance(node, ast.ListComp) and narrative_value(node.elt)


def appended_narrative(function: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> bool:
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in FILLERS
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == name
        and any(narrative_value(argument) for argument in node.args)
        for node in ast.walk(function)
    )


def local_lists(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    for node in ast.walk(function):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) and node.value is not None else []
        value = node.value if isinstance(node, ast.Assign | ast.AnnAssign) else None
        if value is None or not isinstance(value, ast.List | ast.ListComp):
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id in NAMES and (narrative_list(value) or appended_narrative(function, target.id)):
                found.append((target.id, node.lineno))
    return found


def passed_on(function: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> bool:
    for node in ast.walk(function):
        if isinstance(node, ast.Call) and name in recorded_names(node):
            return True
        if isinstance(node, ast.Return) and node.value is not None and any(isinstance(inner, ast.Name) and inner.id == name for inner in ast.walk(node.value)):
            return True
    return False


def dropped(files: dict[Path, ast.Module]) -> list[Dropped]:
    declared = [(path, *field) for path, tree in files.items() for field in declared_fields(tree)]
    classes = {name for _, name, _, _ in declared}
    filled: set[tuple[str, str]] = set()
    reached: set[str] = set()
    for tree in files.values():
        filled |= fills(tree, classes)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                reached |= recorded_names(node)
    found: list[Dropped] = []
    for path, owner, field, line in declared:
        if not ({("*", field), (owner, field), (owner, "*positional")} & filled):
            found.append(Dropped(path, line, f"{owner}.{field} is declared but never filled"))
        elif f".{field}" not in reached:
            found.append(
                Dropped(
                    path,
                    line,
                    f"{owner}.{field} collects a {field} list that never reaches the record API (record, write_steps, StepDraft)",
                )
            )
    by_function: dict[Path, list[ast.FunctionDef | ast.AsyncFunctionDef]] = defaultdict(list)
    for path, tree in files.items():
        by_function[path].extend(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef))
    for path, functions in by_function.items():
        for function in functions:
            for name, line in local_lists(function):
                if not passed_on(function, name):
                    found.append(
                        Dropped(
                            path,
                            line,
                            f"{function.name} collects a local {name} list that never reaches the record API or its caller",
                        )
                    )
    return found


def main() -> int:
    files = {path: ast.parse(path.read_text(encoding="utf-8")) for path in sorted(ENGINE.rglob("*.py")) if not path.is_relative_to(RECORD_API)}
    found = dropped(files)
    for item in found:
        print(f"{item.path.relative_to(ROOT)}:{item.line}: {item.reason}")
    print(f"dropped records: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
