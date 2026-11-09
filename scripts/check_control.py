import ast
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from check_wiring import BOOKKEEPING_TABLES

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "backend/src"
PACKAGE = SRC / "aerona"
FRONTEND = ROOT / "frontend/src"
CATALOG = "aerona.services.player.catalog"
SKIPPED = frozenset({"__pycache__", "alembic", "migration"})
NODE_TABLES = frozenset({"nodes", "entities", "sons", "worlds", "stars", "foreign_gods", "creator"})
FIXED_COLUMNS = frozenset({"id", "locked", "created_at", "updated_at"})
SOFT_DELETE = frozenset(
    {"status", "ended_epoch", "end_epoch", "dissolved_epoch", "retired_epoch", "cured_epoch", "abandoned_epoch", "closed_epoch", "completed_epoch", "active"}
)
VERBS = ("create", "edit", "delete")
GENERIC = {verb: f"record_row:{verb}" for verb in VERBS}
NODE_KEY = re.compile(r"ForeignKey\(['\"](" + "|".join(sorted(NODE_TABLES)) + r")\.")
DEPTH = 6
Key = tuple[str, str]


STATEMENT_VERBS = {"insert": "create", "delete": "delete", "update": "edit"}


@dataclass
class Table:
    name: str
    row: str
    primary: list[str] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    node_columns: list[str] = field(default_factory=list)


def module_name(path: Path) -> str:
    parts = list(path.relative_to(SRC).with_suffix("").parts)
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def load_modules() -> dict[str, ast.Module]:
    return {module_name(path): ast.parse(path.read_text(encoding="utf-8")) for path in PACKAGE.rglob("*.py") if not SKIPPED.intersection(path.parts)}


class Code:
    def __init__(self, modules: dict[str, ast.Module]) -> None:
        self.modules = modules
        self.imports: dict[str, dict[str, tuple[str, str | None]]] = {}
        self.defs: dict[Key, list[ast.FunctionDef | ast.AsyncFunctionDef]] = {}
        self.tables: dict[str, Table] = {}
        self.rows: dict[str, str] = {}
        self.registered: set[str] = set()
        for name, tree in modules.items():
            self.index(name, tree)
        self.returns: dict[Key, set[str]] = {
            key: self.annotated(nodes[0].returns) for key, nodes in self.defs.items() if len(nodes) == 1 and nodes[0].returns is not None
        }
        self.facts: dict[Key, dict[str, set[str]]] = {}
        self.callees: dict[Key, set[Key]] = {}

    def index(self, name: str, tree: ast.Module) -> None:
        table: dict[str, tuple[str, str | None]] = {}
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module:
                base = node.module if not node.level else ".".join([*name.split(".")[: -node.level], node.module])
                for alias in node.names:
                    full = f"{base}.{alias.name}"
                    table[alias.asname or alias.name] = (full, None) if full in self.modules else (base, alias.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.defs[(name, node.name)] = [node]
            elif isinstance(node, ast.ClassDef):
                methods = [item for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))]
                if methods:
                    self.defs[(name, node.name)] = methods
                if name.startswith("aerona.db.tables"):
                    self.table_of(node)
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and getattr(node.value.func, "id", "") == "register_profile_table":
                first = node.value.args[0] if node.value.args else None
                if isinstance(first, ast.Constant):
                    self.registered.add(str(first.value))
                elif isinstance(first, ast.Attribute) and isinstance(first.value, ast.Name):
                    self.registered.add(f"row:{first.value.id}")
        self.imports[name] = table

    def table_of(self, node: ast.ClassDef) -> None:
        name = next(
            (
                str(item.value.value)
                for item in node.body
                if isinstance(item, ast.Assign)
                and any(getattr(target, "id", "") == "__tablename__" for target in item.targets)
                and isinstance(item.value, ast.Constant)
            ),
            None,
        )
        if name is None:
            return
        table = Table(name, node.name)
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name) and "Mapped[" in ast.unparse(item.annotation):
                text = ast.unparse(item)
                table.columns.append(item.target.id)
                if "primary_key=True" in text:
                    table.primary.append(item.target.id)
                if NODE_KEY.search(text):
                    table.node_columns.append(item.target.id)
        self.tables[name] = table
        self.rows[node.name] = name

    def annotated(self, node: ast.AST | None) -> set[str]:
        return {self.rows[sub.id] for sub in ast.walk(node) if isinstance(sub, ast.Name) and sub.id in self.rows} if node is not None else set()

    def resolve(self, module: str, ref: str) -> Key | None:
        if (module, ref) in self.defs:
            return (module, ref)
        found = self.imports.get(module, {}).get(ref)
        hops = 0
        while found is not None and found[1] is not None and hops < DEPTH:
            target = (found[0], found[1])
            if target in self.defs:
                return target
            found = self.imports.get(found[0], {}).get(found[1])
            hops += 1
        return None

    def module_ref(self, module: str, ref: str) -> str | None:
        found = self.imports.get(module, {}).get(ref)
        return found[0] if found is not None and found[1] is None and found[0] in self.modules else None

    def selected(self, node: ast.AST) -> set[str]:
        return {
            self.rows[arg.id]
            for sub in ast.walk(node)
            if isinstance(sub, ast.Call) and getattr(sub.func, "id", "") == "select"
            for arg in sub.args
            if isinstance(arg, ast.Name) and arg.id in self.rows
        }

    def kind(self, module: str, env: dict[str, set[str]], expr: ast.AST) -> set[str]:
        if isinstance(expr, ast.Await | ast.Subscript):
            return self.kind(module, env, expr.value)
        if isinstance(expr, ast.Name):
            return set(env.get(expr.id, set()))
        if isinstance(expr, (ast.ListComp, ast.GeneratorExp, ast.SetComp)):
            return self.kind(module, env, expr.generators[0].iter) if expr.generators else set()
        if isinstance(expr, ast.IfExp):
            return self.kind(module, env, expr.body) | self.kind(module, env, expr.orelse)
        if isinstance(expr, ast.BoolOp):
            return set().union(*(self.kind(module, env, value) for value in expr.values))
        return self.call_kind(module, env, expr) if isinstance(expr, ast.Call) else set()

    def name_kind(self, module: str, env: dict[str, set[str]], expr: ast.Call, func: ast.Name) -> set[str]:
        if func.id in self.rows:
            return {self.rows[func.id]}
        if func.id in {"list", "sorted", "next", "iter", "unheld"} and expr.args:
            return self.kind(module, env, expr.args[0])
        hit = self.resolve(module, func.id)
        if hit is None:
            return self.selected(expr)
        return set(self.returns.get(hit, set())) or {self.rows[arg.id] for arg in expr.args if isinstance(arg, ast.Name) and arg.id in self.rows}

    def call_kind(self, module: str, env: dict[str, set[str]], expr: ast.Call) -> set[str]:
        func = expr.func
        if isinstance(func, ast.Name):
            return self.name_kind(module, env, expr, func)
        if isinstance(func, ast.Attribute):
            if func.attr == "get" and expr.args and isinstance(expr.args[0], ast.Name) and expr.args[0].id in self.rows:
                return {self.rows[expr.args[0].id]}
            if func.attr in {"scalar", "scalars", "execute", "first", "one", "one_or_none", "all"}:
                return self.selected(expr) or self.kind(module, env, func.value)
            if isinstance(func.value, ast.Name):
                owner = self.module_ref(module, func.value.id)
                if owner is not None and (owner, func.attr) in self.returns:
                    return set(self.returns[(owner, func.attr)])
        return self.selected(expr)

    def environment(self, module: str, node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, set[str]]:
        env: dict[str, set[str]] = defaultdict(set)
        for arg in [*node.args.args, *node.args.kwonlyargs, *node.args.posonlyargs]:
            env[arg.arg] |= self.annotated(arg.annotation)
        for _ in range(2):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Assign) and len(sub.targets) == 1:
                    target = sub.targets[0]
                    found = self.kind(module, env, sub.value)
                    names = [target] if isinstance(target, ast.Name) else [item for item in getattr(target, "elts", []) if isinstance(item, ast.Name)]
                    for item in names:
                        env[item.id] |= found
                elif isinstance(sub, ast.AnnAssign) and isinstance(sub.target, ast.Name):
                    env[sub.target.id] |= self.annotated(sub.annotation) | (self.kind(module, env, sub.value) if sub.value else set())
                elif isinstance(sub, (ast.For, ast.AsyncFor, ast.comprehension)) and isinstance(sub.target, ast.Name):
                    env[sub.target.id] |= self.kind(module, env, sub.iter)
                elif isinstance(sub, ast.NamedExpr):
                    env[sub.target.id] |= self.kind(module, env, sub.value)
        return env

    def call_verbs(self, module: str, env: dict[str, set[str]], call: ast.Call, found: dict[str, set[str]]) -> None:
        func = call.func
        first = call.args[0] if call.args else None
        if isinstance(func, ast.Name) and func.id in self.rows:
            found["create"].add(self.rows[func.id])
            return
        if first is None:
            return
        if isinstance(func, ast.Name):
            statement = STATEMENT_VERBS.get(func.id)
            if statement is not None:
                found[statement] |= self.annotated(first)
            elif func.id == "setattr":
                found["edit"] |= self.kind(module, env, first)
        elif isinstance(func, ast.Attribute) and func.attr == "delete":
            found["delete"] |= self.kind(module, env, first)
        elif isinstance(func, ast.Attribute) and func.attr == "merge":
            merged = self.kind(module, env, first)
            found["create"] |= merged
            found["edit"] |= merged

    def verbs(self, module: str, node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, set[str]]:
        env = self.environment(module, node)
        found: dict[str, set[str]] = {verb: set() for verb in VERBS}
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call):
                self.call_verbs(module, env, sub, found)
            elif isinstance(sub, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                targets = sub.targets if isinstance(sub, ast.Assign) else [sub.target]
                for leaf in (item for target in targets for item in ast.walk(target) if isinstance(item, ast.Attribute)):
                    tables = self.kind(module, env, leaf.value)
                    found["edit"] |= tables
                    if leaf.attr in SOFT_DELETE:
                        found["delete"] |= tables
        return found

    def prepare(self, key: Key) -> None:
        if key in self.facts:
            return
        module = key[0]
        merged: dict[str, set[str]] = {verb: set() for verb in VERBS}
        callees: set[Key] = set()
        for node in self.defs[key]:
            for verb, tables in self.verbs(module, node).items():
                merged[verb] |= tables
            for sub in ast.walk(node):
                if isinstance(sub, ast.Name):
                    hit = self.resolve(module, sub.id)
                    if hit is not None and hit != key:
                        callees.add(hit)
                elif isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name):
                    owner = self.module_ref(module, sub.value.id)
                    if owner is not None and (owner, sub.attr) in self.defs:
                        callees.add((owner, sub.attr))
        self.facts[key] = merged
        self.callees[key] = callees

    def reach(self, start: Key) -> dict[str, set[str]]:
        total: dict[str, set[str]] = {verb: set() for verb in VERBS}
        seen: set[Key] = set()
        stack = [(start, 0)]
        while stack:
            key, level = stack.pop()
            if key in seen:
                continue
            seen.add(key)
            self.prepare(key)
            for verb, tables in self.facts[key].items():
                total[verb] |= tables
            if level < DEPTH:
                stack.extend((callee, level + 1) for callee in self.callees[key])
        return total


def levers(code: Code) -> dict[str, Key]:
    found: dict[str, Key] = {}
    for node in ast.walk(code.modules[CATALOG]):
        if not (isinstance(node, ast.Call) and len(node.args) > 1 and isinstance(node.args[0], ast.Call)):
            continue
        meta, handler = node.args[0], node.args[1]
        if getattr(meta.func, "id", "") != "Meta" or not meta.args or not isinstance(meta.args[0], ast.Constant):
            continue
        if isinstance(handler, ast.Attribute) and isinstance(handler.value, ast.Name):
            owner = code.module_ref(CATALOG, handler.value.id)
            if owner is not None and (owner, handler.attr) in code.defs:
                found[str(meta.args[0].value)] = (owner, handler.attr)
    return found


def reachable(ids: dict[str, Key]) -> set[str]:
    frontend = "\n".join(
        path.read_text(encoding="utf-8") for path in FRONTEND.rglob("*.ts*") if "generated" not in path.parts and ".test." not in path.name and path.is_file()
    )
    backend = "\n".join(path.read_text(encoding="utf-8") for path in PACKAGE.rglob("*.py") if not SKIPPED.intersection(path.parts))
    aliased = set(re.findall(r'Alias\(\s*"[A-Z]+",\s*"[^"]+",\s*"([^"]+)"', backend))
    return {lever for lever in ids if lever in frontend or lever in aliased}


def profiled(code: Code, table: Table) -> bool:
    registered = table.name in code.registered or f"row:{table.row}" in code.registered
    return registered or (len(table.primary) == 1 and table.primary[0] in table.node_columns)


def editable(table: Table) -> bool:
    return any(column not in table.primary and column not in table.node_columns and column not in FIXED_COLUMNS for column in table.columns)


def main() -> int:
    code = Code(load_modules())
    written = {name for path in (PACKAGE / "engine").rglob("*.py") for name in re.findall(r'"table\.([a-z_]+)"', path.read_text(encoding="utf-8"))}
    engine_changes: dict[str, set[str]] = defaultdict(set)
    for key in code.defs:
        if key[0].startswith("aerona.engine"):
            code.prepare(key)
            for verb in ("edit", "delete"):
                for table in code.facts[key][verb]:
                    engine_changes[table].add(verb)
    rebuilt = {
        code.rows[name]
        for path in (PACKAGE / "engine").rglob("*.py")
        for name in re.findall(r"execute\(delete\((\w+Row)\)\)", path.read_text(encoding="utf-8"))
        if name in code.rows
    }
    ids = levers(code)
    open_ids = reachable(ids)
    covered: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for lever in sorted(open_ids):
        for verb, tables in code.reach(ids[lever]).items():
            for table in tables:
                covered[table][verb].add(lever)
    errors: list[str] = []
    if "profile:set" not in open_ids:
        errors.append("the generic profile editor profile:set is missing or unreachable from the frontend")
    for name in sorted(written & set(code.tables)):
        table = code.tables[name]
        if name in BOOKKEEPING_TABLES or name in rebuilt or not engine_changes[name] or profiled(code, table):
            continue
        wanted = [verb for verb in VERBS if verb != "edit" or editable(table)]
        generic = {verb for verb, lever in GENERIC.items() if lever in open_ids and table.node_columns and name not in NODE_TABLES}
        missing = [verb for verb in wanted if not covered[name][verb] and verb not in generic]
        if missing:
            errors.append(f"table {name} is state the engine changes, but no frontend-reachable god lever can {' or '.join(missing)} its rows")
    for line in errors:
        print(f"ERROR {line}")
    print(f"control: {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
