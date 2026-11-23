import ast
import sys
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
sys.path.insert(0, str(SOURCE.parent))

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.domain.enums.records import PlaceRule

RECORDERS = frozenset({"record", "record_happening"})
RECORD_MODULE = "aerona.engine.recording.record"
STEP_ENUM = "StepAction"
STEP_DRAFT = "StepDraft"


@dataclass(frozen=True)
class Stray:
    path: Path
    line: int
    key: str
    action: str


@dataclass(frozen=True)
class Module:
    path: Path
    tree: ast.Module
    constants: dict[str, str]
    imports: dict[str, tuple[str, str]]
    step_names: frozenset[str]
    recorders: frozenset[str]


def dotted(path: Path) -> str:
    return ".".join(path.relative_to(SOURCE.parent).with_suffix("").parts)


def parse(path: Path, text: str) -> Module:
    tree = ast.parse(text)
    constants: dict[str, str] = {}
    imports: dict[str, tuple[str, str]] = {}
    step_names = {STEP_ENUM}
    recorders = set(RECORDERS)
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    constants[target.id] = node.value.value
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            constants[node.target.id] = node.value.value
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                local = alias.asname or alias.name
                imports[local] = (node.module, alias.name)
                if alias.name == STEP_ENUM:
                    step_names.add(local)
                if node.module == RECORD_MODULE and alias.name == "record":
                    recorders.add(local)
    return Module(path, tree, constants, imports, frozenset(step_names), frozenset(recorders))


def key_of(node: ast.expr, module: Module, modules: Mapping[str, Module]) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in module.constants:
            return module.constants[node.id]
        source = module.imports.get(node.id)
        if source is not None and source[0] in modules:
            return modules[source[0]].constants.get(source[1])
    return None


def recorder(call: ast.Call, module: Module) -> str | None:
    if isinstance(call.func, ast.Name) and call.func.id in module.recorders:
        return call.func.id
    if isinstance(call.func, ast.Attribute) and call.func.attr in RECORDERS:
        return call.func.attr
    return None


def actions_in(node: ast.AST, step_names: frozenset[str]) -> Iterator[str]:
    for inner in ast.walk(node):
        if not (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) and inner.func.id == STEP_DRAFT):
            continue
        given = inner.args[0] if inner.args else next((item.value for item in inner.keywords if item.arg == "action"), None)
        if isinstance(given, ast.Attribute) and isinstance(given.value, ast.Name) and given.value.id in step_names:
            yield given.attr


def own_nodes(function: ast.AST) -> Iterator[ast.AST]:
    pending = list(ast.iter_child_nodes(function))
    while pending:
        node = pending.pop()
        yield node
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            pending.extend(ast.iter_child_nodes(node))


def bound_value(node: ast.AST, name: str) -> ast.expr | None:
    if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
        return node.value
    if isinstance(node, (ast.AnnAssign, ast.AugAssign)) and isinstance(node.target, ast.Name) and node.target.id == name:
        return node.value
    return None


def assigned(function: ast.AST, name: str) -> Iterator[ast.AST]:
    for node in own_nodes(function):
        value = bound_value(node, name)
        if value is not None:
            yield value
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"append", "extend"}
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == name
        ):
            yield from node.args


def functions(tree: ast.Module) -> Iterator[ast.AST]:
    yield tree
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def strays(sources: Mapping[Path, str], declared: Mapping[str, frozenset[str]]) -> list[Stray]:
    modules = {dotted(path): parse(path, text) for path, text in sources.items()}
    found: set[Stray] = set()
    for module in modules.values():
        for function in functions(module.tree):
            for call in own_nodes(function):
                if not isinstance(call, ast.Call) or recorder(call, module) is None:
                    continue
                steps = next((item.value for item in call.keywords if item.arg == "steps"), None)
                if steps is None:
                    continue
                key = next((found_key for arg in call.args if (found_key := key_of(arg, module, modules)) is not None), None)
                if key is None or key not in declared:
                    continue
                sources_of = [steps] if not isinstance(steps, ast.Name) else list(assigned(function, steps.id))
                for source in sources_of:
                    for action in actions_in(source, module.step_names):
                        if action.lower() not in declared[key]:
                            found.add(Stray(module.path, call.lineno, key, action.lower()))
    return sorted(found, key=lambda item: (str(item.path), item.line, item.action))


def recorded_keys(sources: Mapping[Path, str]) -> Iterator[tuple[Module, ast.Call, str]]:
    modules = {dotted(path): parse(path, text) for path, text in sources.items()}
    for module in modules.values():
        for function in functions(module.tree):
            for call in own_nodes(function):
                if not isinstance(call, ast.Call) or recorder(call, module) is None:
                    continue
                key = next((found_key for arg in call.args if (found_key := key_of(arg, module, modules)) is not None), None)
                if key is not None:
                    yield module, call, key


def placeless(sources: Mapping[Path, str], required: frozenset[str]) -> list[Stray]:
    found = {
        Stray(module.path, call.lineno, key, "place")
        for module, call, key in recorded_keys(sources)
        if key in required and not any(item.arg in {"place", None} for item in call.keywords)
    }
    return sorted(found, key=lambda item: (str(item.path), item.line))


def placed_kinds() -> frozenset[str]:
    return frozenset(key for key, spec in INCIDENT_KINDS.items() if spec.place is PlaceRule.REQUIRED)


def declared_steps() -> dict[str, frozenset[str]]:
    return {key: frozenset(step.value for step in spec.steps) for key, spec in INCIDENT_KINDS.items()}


def sources() -> dict[Path, str]:
    return {path: path.read_text(encoding="utf-8") for path in sorted(SOURCE.rglob("*.py")) if "__pycache__" not in path.parts}


def main() -> int:
    code = sources()
    found = strays(code, declared_steps())
    unplaced = placeless(code, placed_kinds())
    for item in found:
        print(
            f"{item.path.relative_to(ROOT)}:{item.line}: {item.key} is recorded with a {item.action} step its kind does not declare, so the happening "
            "fails only when it runs; add the step to the kind's steps or record a step it declares"
        )
    for item in unplaced:
        print(
            f"{item.path.relative_to(ROOT)}:{item.line}: {item.key} needs its place but is recorded with no place=, so the happening fails only "
            "when it runs; pass the place it happened"
        )
    print(f"record steps: {len(found)}, unplaced records: {len(unplaced)}")
    return 1 if found or unplaced else 0


if __name__ == "__main__":
    sys.exit(main())
