import ast
import importlib
import itertools
import re
import sys
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
SPEC = ROOT / "docs" / "spec" / "16-minds-powers-living-craft.md"
SKIPPED = (SOURCE / "db" / "alembic", SOURCE / "catalog" / "incident_kinds")
KEY_SHAPE = re.compile(r"^[a-z][a-z0-9_]*\.[a-z0-9_.]+$")
APPENDIX_ROW = re.compile(r"^\| `([a-z0-9_]+)\.\*` \| (\d+) ")
DEPTH = 4
EXPANSION_MAX = 400
WRITERS = frozenset({"note", "record"})
WRITER_SOURCES = frozenset({"aerona.engine.notes.note", "aerona.engine.recording.record", "aerona.engine.recording.record.record"})
TOOL_RECORDERS = frozenset({"call"})
PLUMBING = frozenset({"engine/context.py", "engine/notes.py", "engine/recording/record.py", "db/repositories/chronicle.py", "tools/framework/call.py"})
ENUM_OVERRIDES = {
    "engine/dominion/creatures.py:266": ("aerona.domain.enums.dominion.CreatureDeed", ()),
    "engine/gatherings/hold.py:gathering.": ("aerona.domain.enums.gathering.GatheringKind", ()),
    "engine/mortal/acts.py:career.": ("aerona.domain.enums.mortal.CareerPath", ()),
    "engine/phases/exploration.py:exploration.route_search.": ("aerona.engine.phases.exploration.SearchStatus", ()),
    "engine/phases/travel.py:travel.road.": ("aerona.domain.enums.travel.JourneyEventKind", ()),
    "engine/sites/digs.py:excavation.": ("aerona.domain.enums.site.ExcavationStage", ()),
    "engine/phases/vendettas.py:215": ("aerona.domain.enums.military.FeudAction", ("mediated",)),
}
EXTRA_KEYS: dict[str, tuple[str, ...]] = {}
GOD_CHOSEN = {"services/player/incidents.py:create_incident": ("player.history",)}
WRAPPERS = frozenset({"Mapped", "Optional", "Final", "ClassVar"})


@dataclass(frozen=True)
class Site:
    path: Path
    line: int
    via: str
    keys: tuple[str, ...]
    unresolved: tuple[str, ...]
    text: ast.expr | None
    ids: tuple[str, ...]
    chronicle_kind: str | None
    feed: str | None
    magnitude: int | None
    has_place: bool
    enum_prefix: tuple[str, str] | None = None

    @property
    def where(self) -> str:
        return f"{self.path.relative_to(SOURCE)}:{self.line}"

    @property
    def rendered(self) -> bool:
        return self.via != "record" and self.text is not None


@dataclass
class Index:
    modules: dict[Path, ast.Module] = field(default_factory=dict)
    parents: dict[int, ast.AST] = field(default_factory=dict)
    calls: dict[str, list[tuple[Path, ast.Call]]] = field(default_factory=lambda: defaultdict(list))
    functions: dict[str, list[tuple[Path, ast.FunctionDef | ast.AsyncFunctionDef]]] = field(default_factory=lambda: defaultdict(list))
    fields: dict[str, dict[str, ast.expr]] = field(default_factory=lambda: defaultdict(dict))
    constants: dict[tuple[Path, str], ast.expr] = field(default_factory=dict)
    imports: dict[Path, dict[str, str]] = field(default_factory=lambda: defaultdict(dict))


def source_files() -> Iterator[Path]:
    for path in sorted(SOURCE.rglob("*.py")):
        if not any(path.is_relative_to(skipped) for skipped in SKIPPED):
            yield path


def module_name(path: Path) -> str:
    return "aerona." + ".".join(path.relative_to(SOURCE).with_suffix("").parts)


def build_index() -> Index:
    index = Index()
    for path in source_files():
        tree = ast.parse(path.read_text())
        index.modules[path] = tree
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                index.parents[id(child)] = node
            if isinstance(node, ast.Call):
                name = called_name(node)
                if name:
                    index.calls[name].append((path, node))
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                index.functions[node.name].append((path, node))
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        index.fields[node.name][item.target.id] = item.annotation
            if isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    index.imports[path][alias.asname or alias.name] = f"{node.module}.{alias.name}"
        for item in tree.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        index.constants[(path, target.id)] = item.value
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name) and item.value is not None:
                index.constants[(path, item.target.id)] = item.value
    return index


def called_name(call: ast.Call) -> str | None:
    func = call.func
    return func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else None


def enclosing_function(index: Index, node: ast.AST) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    current = index.parents.get(id(node))
    while current is not None:
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return current
        current = index.parents.get(id(current))
    return None


@cache
def enum_classes() -> dict[str, type[Enum]]:
    sys.path.insert(0, str(SOURCE.parent))
    found: dict[str, type[Enum]] = {}
    for path in sorted((SOURCE / "domain" / "enums").glob("*.py")):
        module = importlib.import_module(f"aerona.domain.enums.{path.stem}")
        for name, value in vars(module).items():
            if isinstance(value, type) and issubclass(value, Enum) and value.__module__ == module.__name__:
                found.setdefault(name, value)
    return found


def annotation_name(annotation: ast.expr | None) -> str | None:
    if annotation is None:
        return None
    if isinstance(annotation, ast.Subscript) and isinstance(annotation.value, ast.Name) and annotation.value.id in WRAPPERS:
        return annotation_name(annotation.slice)
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        left, right = annotation_name(annotation.left), annotation_name(annotation.right)
        return left if left not in (None, "None") else right
    if isinstance(annotation, ast.Name):
        return annotation.id
    if isinstance(annotation, ast.Attribute):
        return annotation.attr
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        return annotation.value
    return None


def type_of(index: Index, expr: ast.expr, function: ast.AST | None, depth: int = 0) -> str | None:
    if depth > DEPTH:
        return None
    if isinstance(expr, ast.Name):
        return name_type(index, expr.id, function, depth)
    if isinstance(expr, ast.Attribute):
        if isinstance(expr.value, ast.Name) and expr.value.id in enum_classes():
            return expr.value.id
        owner = type_of(index, expr.value, function, depth + 1)
        if owner is not None and expr.attr in index.fields.get(owner, {}):
            return annotation_name(index.fields[owner][expr.attr])
        return None
    if isinstance(expr, ast.Await):
        return type_of(index, expr.value, function, depth + 1)
    if isinstance(expr, ast.IfExp):
        return type_of(index, expr.body, function, depth + 1) or type_of(index, expr.orelse, function, depth + 1)
    if isinstance(expr, ast.Call):
        name = called_name(expr)
        if name in enum_classes() or name in index.fields:
            return name
        if name in ("get", "get_one", "scalar", "first", "one", "scalars") and expr.args:
            selected = selected_row(expr)
            if selected is not None:
                return selected
        if name == "get" and isinstance(expr.func, ast.Attribute):
            return mapping_value_type(index, expr.func.value, function)
        if name in index.functions:
            returned = annotation_name(index.functions[name][0][1].returns)
            if returned not in (None, "None"):
                return returned
    if isinstance(expr, ast.Subscript):
        return mapping_value_type(index, expr.value, function)
    return None


def mapping_value_type(index: Index, holder: ast.expr, function: ast.AST | None) -> str | None:
    if not isinstance(holder, ast.Name):
        return None
    for (path, name), _ in index.constants.items():
        if name != holder.id:
            continue
        for item in index.modules[path].body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name) and item.target.id == name:
                annotation = item.annotation
                if isinstance(annotation, ast.Subscript) and isinstance(annotation.slice, ast.Tuple) and len(annotation.slice.elts) == 2:
                    return annotation_name(annotation.slice.elts[1])
            if isinstance(item, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in item.targets):
                values = item.value.args[0] if isinstance(item.value, ast.Call) and item.value.args else item.value
                if isinstance(values, ast.Dict) and values.values:
                    found = type_of(index, values.values[0], None)
                    if found is not None:
                        return found
    return None


def name_type(index: Index, name: str, function: ast.AST | None, depth: int) -> str | None:
    if function is None:
        return None
    if isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for arg in [*function.args.posonlyargs, *function.args.args, *function.args.kwonlyargs]:
            if arg.arg == name:
                return annotation_name(arg.annotation)
    for node in ast.walk(function):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            return annotation_name(node.annotation)
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            found = type_of(index, node.value, function, depth + 1)
            if found is not None:
                return found
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Tuple):
            for target in node.targets:
                if isinstance(target, ast.Tuple) and len(target.elts) == len(node.value.elts):
                    for part, value in zip(target.elts, node.value.elts, strict=True):
                        if isinstance(part, ast.Name) and part.id == name:
                            found = type_of(index, value, function, depth + 1)
                            if found is not None:
                                return found
        if isinstance(node, (ast.For, ast.comprehension)) and isinstance(node.target, ast.Name) and node.target.id == name:
            found = iterated_type(index, node.iter, function, depth)
            if found is not None:
                return found
    return None


def selected_row(expr: ast.expr) -> str | None:
    for node in ast.walk(expr):
        if isinstance(node, ast.Call) and called_name(node) == "select" and node.args and isinstance(node.args[0], ast.Name):
            return node.args[0].id
    if (
        isinstance(expr, ast.Call)
        and called_name(expr) in ("get", "get_one")
        and expr.args
        and isinstance(expr.args[0], ast.Name)
        and expr.args[0].id.endswith("Row")
    ):
        return expr.args[0].id
    return None


def iterated_type(index: Index, iterable: ast.expr, function: ast.AST | None, depth: int) -> str | None:
    selected = selected_row(iterable)
    if selected is not None:
        return selected
    called = iterable.value if isinstance(iterable, ast.Await) else iterable
    if isinstance(called, ast.Call) and called_name(called) in index.functions:
        returns = index.functions[called_name(called) or ""][0][1].returns
        if isinstance(returns, ast.Subscript):
            inner = returns.slice
            return annotation_name(inner.elts[0] if isinstance(inner, ast.Tuple) else inner)
    if isinstance(iterable, ast.Name) and iterable.id in enum_classes():
        return iterable.id
    if isinstance(iterable, ast.Name) and isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for arg in [*function.args.posonlyargs, *function.args.args, *function.args.kwonlyargs]:
            if arg.arg == iterable.id and isinstance(arg.annotation, ast.Subscript):
                inner = arg.annotation.slice
                return annotation_name(inner.elts[0] if isinstance(inner, ast.Tuple) else inner)
    if isinstance(iterable, ast.Name) and function is not None:
        for node in ast.walk(function):
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == iterable.id for target in node.targets):
                selected = selected_row(node.value)
                if selected is not None:
                    return selected
                inner = iterated_type(index, node.value, function, depth + 1) if depth < DEPTH else None
                if inner is not None:
                    return inner
    if isinstance(iterable, ast.Name):
        held = next((value for (_, name), value in index.constants.items() if name == iterable.id), None)
        held = held.args[0] if isinstance(held, ast.Call) and held.args else held
        if isinstance(held, (ast.Tuple, ast.List, ast.Set)) and held.elts:
            return type_of(index, held.elts[0], None, depth + 1)
    if isinstance(iterable, (ast.Tuple, ast.List, ast.Set)) and iterable.elts:
        return type_of(index, iterable.elts[0], function, depth + 1)
    if isinstance(iterable, ast.Call) and called_name(iterable) in ("sorted", "list", "tuple", "reversed") and iterable.args:
        return iterated_type(index, iterable.args[0], function, depth + 1)
    return None


def returned_strings(index: Index, value: ast.expr) -> ast.expr:
    inner = value.value if isinstance(value, ast.Await) else value
    name = called_name(inner) if isinstance(inner, ast.Call) else None
    bodies = [function for _, function in index.functions.get(name or "", [])]
    return ast.Tuple(elts=[*bodies] or [value], ctx=ast.Load())


def strings_in(expr: ast.expr) -> list[str]:
    return [node.value for node in ast.walk(expr) if isinstance(node, ast.Constant) and isinstance(node.value, str) and KEY_SHAPE.match(node.value)]


def resolve(index: Index, path: Path, expr: ast.expr, function: ast.AST | None, depth: int = 0) -> tuple[set[str], set[str]]:
    if depth > DEPTH:
        return set(), {ast.unparse(expr)}
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return {expr.value}, set()
    if isinstance(expr, ast.IfExp):
        first, missing = resolve(index, path, expr.body, function, depth + 1)
        second, more = resolve(index, path, expr.orelse, function, depth + 1)
        return first | second, missing | more
    if isinstance(expr, ast.BoolOp):
        found, missing = set(), set()
        for value in expr.values:
            keys, gone = resolve(index, path, value, function, depth + 1)
            found |= keys
            missing |= gone
        return found, missing
    if isinstance(expr, ast.JoinedStr):
        return expand_fstring(index, path, expr, function, depth)
    if isinstance(expr, ast.Name):
        return resolve_name(index, path, expr.id, function, depth)
    if isinstance(expr, ast.Subscript) or (isinstance(expr, ast.Call) and called_name(expr) == "get"):
        keys = set(strings_in(expr))
        holder = expr.value if isinstance(expr, ast.Subscript) else expr.func.value if isinstance(expr.func, ast.Attribute) else None
        if isinstance(holder, ast.Name):
            held = index.constants.get((path, holder.id))
            keys |= set(strings_in(held)) if held is not None else set()
        return (keys, set()) if keys else (set(), {ast.unparse(expr)})
    if isinstance(expr, ast.Attribute):
        return resolve_attribute(index, path, expr, function, depth)
    if isinstance(expr, (ast.Await, ast.Call)):
        keys = set(strings_in(returned_strings(index, expr)))
        return (keys, set()) if keys else (set(), {ast.unparse(expr)})
    return set(), {ast.unparse(expr)}


def held_constant(index: Index, path: Path, expr: ast.expr) -> tuple[Path, ast.expr] | None:
    if isinstance(expr, ast.Name):
        if (path, expr.id) in index.constants:
            return path, index.constants[(path, expr.id)]
        imported = index.imports[path].get(expr.id)
        if imported is not None:
            module, _, symbol = imported.rpartition(".")
            target = SOURCE.parent / Path(*module.split(".")).with_suffix(".py")
            if (target, symbol) in index.constants:
                return target, index.constants[(target, symbol)]
        return None
    if isinstance(expr, ast.Attribute) and isinstance(expr.value, ast.Name):
        imported = index.imports[path].get(expr.value.id)
        if imported is not None:
            target = SOURCE.parent / Path(*imported.split(".")).with_suffix(".py")
            if (target, expr.attr) in index.constants:
                return target, index.constants[(target, expr.attr)]
    return None


def field_keys(call: ast.expr, attr: str) -> set[str]:
    if not isinstance(call, ast.Call):
        return set()
    found = {item.value.value for item in call.keywords if item.arg == attr and isinstance(item.value, ast.Constant) and isinstance(item.value.value, str)}
    if not found and call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
        found = {call.args[0].value}
    return found


def constructed(index: Index, path: Path, attr: str, depth: int, owner: str | None = None) -> tuple[set[str], set[str]]:
    found: set[str] = set()
    missing: set[str] = set()
    calls = (
        [(where, call) for where, call in index.calls.get(owner, [])]
        if owner in index.fields
        else [(path, node) for node in ast.walk(index.modules[path]) if isinstance(node, ast.Call)]
    )
    for where, node in calls:
        path = where
        name = called_name(node)
        fields = list(index.fields.get(name or "", {}))
        if attr not in fields:
            continue
        given = next((item.value for item in node.keywords if item.arg == attr), None)
        position = fields.index(attr)
        if given is None and position < len(node.args):
            given = node.args[position]
        if given is None:
            continue
        keys, gone = resolve(index, path, given, enclosing_function(index, node), depth + 1)
        found |= {key for key in keys if KEY_SHAPE.match(key)}
        missing |= gone
    return found, missing


def resolve_attribute(index: Index, path: Path, expr: ast.Attribute, function: ast.AST | None = None, depth: int = 0) -> tuple[set[str], set[str]]:
    root = expr.value
    sources: list[ast.expr] = [root]
    if isinstance(root, ast.Name) and function is not None:
        sources += [
            node.value for node in ast.walk(function) if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == root.id for t in node.targets)
        ]
    direct: set[str] = set()
    for source in sources:
        held = held_constant(index, path, source)
        if held is not None:
            direct |= field_keys(held[1], expr.attr)
        elif isinstance(source, ast.IfExp):
            for branch in (source.body, source.orelse):
                branch_held = held_constant(index, path, branch)
                if branch_held is not None:
                    direct |= field_keys(branch_held[1], expr.attr)
    direct = {key for key in direct if KEY_SHAPE.match(key)}
    if direct:
        return direct, set()
    owner = type_of(index, root, function) if depth < DEPTH else None
    built, gaps = constructed(index, path, expr.attr, depth + 1, owner) if depth < DEPTH else (set(), set())
    if built:
        return built, gaps
    keys: set[str] = set()
    for node in ast.walk(index.modules[path]):
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg == expr.attr and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
                    keys.add(keyword.value.value)
    keys = {key for key in keys if KEY_SHAPE.match(key)}
    return (keys, set()) if keys else (set(), {ast.unparse(expr)})


def resolve_name(index: Index, path: Path, name: str, function: ast.AST | None, depth: int) -> tuple[set[str], set[str]]:
    if function is not None:
        assigned = [
            node.value for node in ast.walk(function) if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets)
        ]
        assigned += [
            node.value
            for node in ast.walk(function)
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name and node.value
        ]
        loops = [node.iter for node in ast.walk(function) if isinstance(node, ast.For) and isinstance(node.target, ast.Name) and node.target.id == name]
        loops += [
            node.iter
            for node in ast.walk(function)
            if isinstance(node, ast.For)
            and isinstance(node.target, ast.Tuple)
            and any(isinstance(part, ast.Name) and part.id == name for part in node.target.elts)
        ]
        for node in ast.walk(function):
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Tuple) and any(isinstance(p, ast.Name) and p.id == name for p in t.elts) for t in node.targets
            ):
                target = next(t for t in node.targets if isinstance(t, ast.Tuple))
                position = next(i for i, p in enumerate(target.elts) if isinstance(p, ast.Name) and p.id == name)
                if isinstance(node.value, ast.Tuple) and position < len(node.value.elts):
                    assigned.append(node.value.elts[position])
                else:
                    loops.append(returned_strings(index, node.value))
        if assigned or loops:
            found, missing = set(), set()
            for value in assigned:
                keys, gone = resolve(index, path, value, function, depth + 1)
                found |= keys
                missing |= gone
            for loop in loops:
                if isinstance(loop, ast.Name):
                    made = [
                        node.value
                        for node in ast.walk(function)
                        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == loop.id for t in node.targets)
                    ]
                    if made and isinstance(made[0], (ast.Call, ast.Await)):
                        loop = returned_strings(index, made[0])
                held = held_constant(index, path, loop) if isinstance(loop, (ast.Name, ast.Attribute)) else None
                keys = set(strings_in(held[1] if held is not None else loop))
                found |= keys
                if not keys:
                    missing.add(ast.unparse(loop))
            return found, missing
        if isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            params = [arg.arg for arg in [*function.args.posonlyargs, *function.args.args]]
            keyword_params = [arg.arg for arg in function.args.kwonlyargs]
            if name in params or name in keyword_params:
                return resolve_parameter(index, function, name, params, depth)
    constant = index.constants.get((path, name))
    if constant is not None:
        return resolve(index, path, constant, None, depth + 1)
    imported = index.imports[path].get(name)
    if imported is not None:
        module, _, symbol = imported.rpartition(".")
        target = SOURCE.parent / Path(*module.split(".")).with_suffix(".py")
        held = index.constants.get((target, symbol))
        if held is not None:
            return resolve(index, target, held, None, depth + 1)
    return set(), {name}


def resolve_parameter(index: Index, function: ast.FunctionDef | ast.AsyncFunctionDef, name: str, params: list[str], depth: int) -> tuple[set[str], set[str]]:
    offset = 1 if params and params[0] in ("self", "cls") else 0
    position = params.index(name) - offset if name in params else None
    found, missing = set(), set()
    home = next((path for path, defined in index.functions.get(function.name, []) if defined is function), None)
    callers = [
        (path, call)
        for path, call in index.calls.get(function.name, [])
        if path == home or index.imports[path].get(function.name, "").startswith(module_name(home) if home else "")
    ]
    for path, call in callers:
        given = next((keyword.value for keyword in call.keywords if keyword.arg == name), None)
        if given is None and position is not None and 0 <= position < len(call.args) and not isinstance(call.args[position], ast.Starred):
            given = call.args[position]
        if given is None:
            default = parameter_default(function, name)
            if default is not None:
                keys, gone = resolve(index, path, default, None, depth + 1)
                found |= keys
                missing |= gone
            continue
        keys, gone = resolve(index, path, given, enclosing_function(index, call), depth + 1)
        found |= keys
        missing |= gone
    if not callers:
        missing.add(f"{function.name}({name})")
    return found, missing


def parameter_default(function: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> ast.expr | None:
    positional = [*function.args.posonlyargs, *function.args.args]
    defaults = (
        dict(zip([arg.arg for arg in positional][-len(function.args.defaults) :], function.args.defaults, strict=False)) if function.args.defaults else {}
    )
    for arg, default in zip(function.args.kwonlyargs, function.args.kw_defaults, strict=True):
        if default is not None:
            defaults[arg.arg] = default
    return defaults.get(name)


def expand_fstring(index: Index, path: Path, expr: ast.JoinedStr, function: ast.AST | None, depth: int) -> tuple[set[str], set[str]]:
    choices: list[list[str]] = []
    missing: set[str] = set()
    for part in expr.values:
        if isinstance(part, ast.Constant):
            choices.append([str(part.value)])
            continue
        if not isinstance(part, ast.FormattedValue):
            return set(), {ast.unparse(expr)}
        value = part.value
        if isinstance(value, ast.Attribute) and value.attr == "value":
            enum_name = type_of(index, value.value, function)
            enum = enum_classes().get(enum_name or "")
            if enum is not None:
                choices.append([str(member.value) for member in enum])
                continue
            return set(), {ast.unparse(expr)}
        keys, gone = resolve(index, path, value, function, depth + 1)
        words = {key for key in keys} | {node.value for node in ast.walk(value) if isinstance(node, ast.Constant) and isinstance(node.value, str)}
        if not words:
            return set(), {ast.unparse(expr)}
        if gone:
            missing.add(ast.unparse(expr))
        choices.append(sorted(words))
    combos = 1
    for options in choices:
        combos *= len(options)
    if combos > EXPANSION_MAX:
        return set(), {ast.unparse(expr)}
    keys = {"".join(parts) for parts in itertools.product(*choices)}
    return {key for key in keys if KEY_SHAPE.match(key)}, missing


def enum_prefix(index: Index, expr: ast.expr | None, function: ast.AST | None) -> tuple[str, str] | None:
    if not isinstance(expr, ast.JoinedStr) or len(expr.values) != 2:
        return None
    head, tail = expr.values
    if not (isinstance(head, ast.Constant) and isinstance(tail, ast.FormattedValue) and isinstance(tail.value, ast.Attribute) and tail.value.attr == "value"):
        return None
    enum_name = type_of(index, tail.value.value, function)
    return (str(head.value), enum_name) if enum_name in enum_classes() else None


def overridden(expr: ast.JoinedStr, qualified: str, extra: tuple[str, ...]) -> set[str]:
    module, _, name = qualified.rpartition(".")
    sys.path.insert(0, str(SOURCE.parent))
    enum = getattr(importlib.import_module(module), name)
    head = "".join(
        str(part.value)
        for part in expr.values[: next(i for i, part in enumerate(expr.values) if isinstance(part, ast.FormattedValue))]
        if isinstance(part, ast.Constant)
    )
    tail = "".join(
        str(part.value)
        for part in expr.values[[i for i, part in enumerate(expr.values) if isinstance(part, ast.FormattedValue)][-1] + 1 :]
        if isinstance(part, ast.Constant)
    )
    return {f"{head}{value}{tail}" for value in [*(str(member.value) for member in enum), *extra]}


def keyword(call: ast.Call, name: str) -> ast.expr | None:
    return next((item.value for item in call.keywords if item.arg == name), None)


def attribute_value(expr: ast.expr | None) -> str | None:
    owned = isinstance(expr, ast.Attribute) and isinstance(expr.value, ast.Name) and expr.value.id in ("ChronicleKind", "FeedCategory")
    return expr.attr.lower() if owned and isinstance(expr, ast.Attribute) else None


def write_sites(index: Index | None = None) -> list[Site]:
    index = index or build_index()
    sites: list[Site] = []
    for path, tree in index.modules.items():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = called_name(node)
            source = index.imports[path].get(name or "")
            tool_record = name == "record" and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id in TOOL_RECORDERS
            if tool_record:
                via = "record"
            elif source in WRITER_SOURCES and isinstance(node.func, ast.Name):
                via = "note" if source.endswith(".note") else "record"
            else:
                via = "draft" if name == "ChronicleDraft" else name if name in WRITERS or name == "chronicle" else None
                if via in WRITERS:
                    via = None
            if via is None:
                continue
            key_expr = keyword(node, "key") if via in WRITERS else keyword(node, "template_key")
            if via == "record" and key_expr is None and tool_record and node.args:
                key_expr = node.args[0]
            elif via == "record" and key_expr is None and len(node.args) > 1:
                key_expr = node.args[1]
            if via == "note" and not node.args:
                continue
            if via == "chronicle" and isinstance(node.func, ast.Name):
                continue
            if path.relative_to(SOURCE).as_posix() in PLUMBING:
                continue
            function = enclosing_function(index, node)
            text = None if via == "record" else keyword(node, "text") or (node.args[1] if len(node.args) > 1 else None)
            if via == "draft":
                text = keyword(node, "text")
            ids = keyword(node, "ids") or keyword(node, "entity_ids")
            kind = keyword(node, "kind") if via != "chronicle" else (node.args[0] if node.args else keyword(node, "kind"))
            magnitude = keyword(node, "magnitude")
            if key_expr is None and via == "chronicle" and len(node.args) > 1:
                held = held_constant(index, path, node.args[1])
                line_keys = field_keys(held[1], "key") if held is not None else set()
                if line_keys:
                    sites.append(
                        Site(
                            path,
                            node.lineno,
                            "line",
                            tuple(sorted(line_keys)),
                            (),
                            held[1].args[1] if held is not None and isinstance(held[1], ast.Call) and len(held[1].args) > 1 else None,
                            (),
                            attribute_value(kind),
                            None,
                            None,
                            False,
                        )
                    )
                    continue
            if key_expr is None:
                sites.append(
                    Site(path, node.lineno, via, (), ("<no key>",), text, (), attribute_value(kind), attribute_value(keyword(node, "feed")), None, False)
                )
                continue
            keys, missing = resolve(index, path, key_expr, function)
            keys = {key for key in keys if KEY_SHAPE.match(key)}
            override = ENUM_OVERRIDES.get(f"{path.relative_to(SOURCE).as_posix()}:{node.lineno}")
            pattern = key_expr
            if isinstance(key_expr, ast.Name) and function is not None:
                pattern = next(
                    (
                        item.value
                        for item in ast.walk(function)
                        if isinstance(item, ast.Assign)
                        and isinstance(item.value, ast.JoinedStr)
                        and any(isinstance(t, ast.Name) and t.id == key_expr.id for t in item.targets)
                    ),
                    key_expr,
                )
            if override is None and isinstance(pattern, ast.JoinedStr) and pattern.values and isinstance(pattern.values[0], ast.Constant):
                override = ENUM_OVERRIDES.get(f"{path.relative_to(SOURCE).as_posix()}:{pattern.values[0].value}")
            if override is not None and isinstance(pattern, ast.JoinedStr):
                keys, missing = overridden(pattern, *override), set()
            extra = EXTRA_KEYS.get(f"{path.relative_to(SOURCE).as_posix()}:{node.lineno}")
            if extra is not None:
                keys, missing = keys | set(extra), set()
            chosen = GOD_CHOSEN.get(f"{path.relative_to(SOURCE).as_posix()}:{getattr(function, 'name', '')}")
            if chosen is not None:
                keys, missing = keys | set(chosen), set()
            sites.append(
                Site(
                    path,
                    node.lineno,
                    via,
                    tuple(sorted(keys)),
                    tuple(sorted(missing)),
                    text,
                    tuple(ast.unparse(item) for item in ids.elts) if isinstance(ids, (ast.List, ast.Tuple)) else (),
                    attribute_value(kind),
                    attribute_value(keyword(node, "feed") or keyword(node, "feed_category")),
                    magnitude.value if isinstance(magnitude, ast.Constant) and isinstance(magnitude.value, int) else None,
                    keyword(node, "place_entity_id") is not None or keyword(node, "place") is not None,
                    enum_prefix(index, key_expr, function),
                )
            )
    sites.extend(declared_lines(index))
    return sites


def declared_lines(index: Index) -> list[Site]:
    found: list[Site] = []
    for path, tree in index.modules.items():
        for item in tree.body:
            if not isinstance(item, (ast.Assign, ast.AnnAssign)) or item.value is None:
                continue
            for value in ast.walk(item.value):
                if not (isinstance(value, ast.Call) and called_name(value) == "Line" and len(value.args) >= 2):
                    continue
                key, text = value.args[0], value.args[1]
                if isinstance(key, ast.Constant) and isinstance(key.value, str) and KEY_SHAPE.match(key.value):
                    found.append(Site(path, value.lineno, "line", (key.value,), (), text, (), None, None, None, False))
    return found


def appendix_groups() -> dict[str, int]:
    found: dict[str, int] = {}
    inside = False
    for line in SPEC.read_text().splitlines():
        if line.startswith("### Appendix 49.A"):
            inside = True
            continue
        if inside and line.startswith("### "):
            break
        match = APPENDIX_ROW.match(line) if inside else None
        if match:
            found[match.group(1)] = int(match.group(2))
    return found
