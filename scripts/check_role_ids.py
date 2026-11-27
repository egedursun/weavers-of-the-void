import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_held_ids import bound_names, row_classes

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
TABLES = SOURCE / "db" / "tables"
NODE_KEYWORDS = frozenset(
    {
        "subject_id",
        "holder_id",
        "holder_node_id",
        "subject_node_id",
        "target_node_id",
        "source_node_id",
        "actor_node_id",
        "node_id",
        "mourner_node_id",
        "deceased_node_id",
    }
)
RECORDERS = frozenset({"record", "record_line"})


@dataclass(frozen=True)
class Stray:
    path: Path
    line: int
    name: str
    table: str
    sink: str


@dataclass
class Schema:
    plain_rows: set[str]
    node_rows: set[str]
    plain_tables: set[str] = field(default_factory=set)
    tables: dict[str, str] = field(default_factory=dict)
    pointers: dict[tuple[str, str], str] = field(default_factory=dict)


def schema() -> Schema:
    nodes, plain = row_classes()
    found = Schema(plain, nodes)
    tables: dict[str, str] = {}
    for path in sorted(TABLES.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.ClassDef):
                continue
            for statement in node.body:
                if (
                    isinstance(statement, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == "__tablename__" for target in statement.targets)
                    and isinstance(statement.value, ast.Constant)
                    and isinstance(statement.value.value, str)
                ):
                    tables[node.name] = statement.value.value
                if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name) and statement.value is not None:
                    for call in ast.walk(statement.value):
                        if isinstance(call, ast.Call) and ast.unparse(call.func).endswith("ForeignKey") and call.args:
                            first = call.args[0]
                            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                                found.pointers[(node.name, statement.target.id)] = first.value.split(".")[0]
    found.plain_tables = {table for name, table in tables.items() if name in plain}
    found.tables = tables
    return found


def value_parts(node: ast.AST) -> list[ast.AST]:
    if isinstance(node, ast.IfExp):
        return [node.body, node.orelse]
    if isinstance(node, ast.Await | ast.Starred):
        return [node.value]
    if isinstance(node, ast.Call):
        return list(node.args)
    if isinstance(node, ast.BinOp):
        return [node.left, node.right]
    if isinstance(node, ast.List | ast.Tuple | ast.Set):
        return list(node.elts)
    return []


def value_names(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    return [name for part in value_parts(node) for name in value_names(part)]


class Flow(ast.NodeVisitor):
    def __init__(self, known: Schema, sinks: dict[str, dict[str | int, str]]) -> None:
        self.known = known
        self.sinks = sinks
        self.scopes: list[dict[str, str]] = [{}]
        self.found: list[tuple[int, str, str, str]] = []

    def visit(self, node: ast.AST) -> None:
        if isinstance(node, ast.ListComp | ast.SetComp | ast.GeneratorExp | ast.DictComp):
            self.visit_comprehension_like(node)
        else:
            super().visit(node)

    def table_of(self, name: str) -> str | None:
        return next((scope[name] for scope in reversed(self.scopes) if name in scope), None)

    def plain_id(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return self.table_of(node.id)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            row = self.table_of(f"row:{node.value.id}")
            if row is None:
                return None
            return self.known.tables.get(row, row) if node.attr == "id" else self.pointer(row, node.attr)
        return None

    def pointer(self, row_class: str, column: str) -> str | None:
        target = self.known.pointers.get((row_class, column))
        return target if target in self.known.plain_tables else None

    def selected(self, source: ast.AST) -> str | None:
        tables: set[str] = set()
        calls = [item for item in ast.walk(source) if isinstance(item, ast.Call) and ast.unparse(item.func).rsplit(".", 1)[-1] == "select"]
        for call in calls:
            for argument in call.args:
                if not (isinstance(argument, ast.Attribute) and isinstance(argument.value, ast.Name)):
                    return None
                owner = argument.value.id
                if argument.attr == "id" and owner in self.known.plain_rows:
                    tables.add(self.known.tables.get(owner, owner))
                    continue
                target = self.pointer(owner, argument.attr)
                if target is None:
                    return None
                tables.add(target)
        if not calls:
            tables = {table for name in value_names(source) if (table := self.table_of(name)) is not None}
        return next(iter(tables)) if len(tables) == 1 else None

    def rows_of(self, source: ast.AST) -> str | None:
        for item in ast.walk(source):
            if isinstance(item, ast.Call):
                name = ast.unparse(item.func).rsplit(".", 1)[-1]
                first = item.args[0] if item.args else None
                if isinstance(first, ast.Name) and first.id in self.known.plain_rows and name in {"select", "get"}:
                    return first.id
        return None

    def bind(self, targets: list[ast.expr], source: ast.AST) -> None:
        rows = self.rows_of(source)
        plain = None if rows is not None else self.selected(source)
        for target in targets:
            for name in bound_names(target):
                for key in (name, f"row:{name}"):
                    self.scopes[-1].pop(key, None)
                if rows is not None:
                    self.scopes[-1][f"row:{name}"] = rows
                elif plain is not None:
                    self.scopes[-1][name] = plain

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.enter_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.enter_function(node)

    def enter_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.scopes.append({})
        for argument in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]:
            if argument.annotation is not None:
                names = {item.id for item in ast.walk(argument.annotation) if isinstance(item, ast.Name)}
                plain = names & self.known.plain_rows
                if len(plain) == 1 and not names & self.known.node_rows:
                    self.scopes[-1][f"row:{argument.arg}"] = next(iter(plain))
        for statement in node.body:
            self.visit(statement)
        self.scopes.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        self.generic_visit(node)
        self.bind(node.targets, node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self.generic_visit(node)
        if node.value is not None:
            self.bind([node.target], node.value)

    def visit_For(self, node: ast.For) -> None:
        self.enter_loop(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.enter_loop(node)

    def enter_loop(self, node: ast.For | ast.AsyncFor) -> None:
        self.visit(node.iter)
        self.bind([node.target], node.iter)
        for statement in [*node.body, *node.orelse]:
            self.visit(statement)

    def visit_comprehension_like(self, node: ast.ListComp | ast.SetComp | ast.GeneratorExp | ast.DictComp) -> None:
        self.scopes.append({})
        for generator in node.generators:
            self.visit(generator.iter)
            self.bind([generator.target], generator.iter)
            for condition in generator.ifs:
                self.visit(condition)
        for part in (node.key, node.value) if isinstance(node, ast.DictComp) else (node.elt,):
            self.visit(part)
        self.scopes.pop()

    def flag(self, node: ast.AST, line: int, sink: str) -> None:
        table = self.plain_id(node)
        if table is not None:
            self.found.append((line, ast.unparse(node), table, sink))

    def visit_Call(self, node: ast.Call) -> None:
        self.generic_visit(node)
        name = ast.unparse(node.func).rsplit(".", 1)[-1]
        for keyword in node.keywords:
            if keyword.arg == "roles" and isinstance(keyword.value, ast.Dict):
                for value in keyword.value.values:
                    for item in value.elts if isinstance(value, ast.List | ast.Tuple) else [value]:
                        self.flag(item, node.lineno, f"a role of {name}")
            elif keyword.arg in NODE_KEYWORDS:
                self.flag(keyword.value, node.lineno, keyword.arg)
        targets = self.sinks.get(name, {})
        for position, argument in enumerate(node.args):
            if position in targets:
                self.flag(argument, node.lineno, f"{name}({targets[position]})")
        for keyword in node.keywords:
            if keyword.arg in targets:
                self.flag(keyword.value, node.lineno, f"{name}({keyword.arg})")


def role_parameters(tree: ast.AST) -> dict[str, dict[str | int, str]]:
    found: dict[str, dict[str | int, str]] = {}
    for function in ast.walk(tree):
        if not isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        parameters = [item.arg for item in [*function.args.posonlyargs, *function.args.args]]
        keywords = {item.arg for item in function.args.kwonlyargs} | set(parameters)
        used: set[str] = set()
        for call in ast.walk(function):
            if not isinstance(call, ast.Call) or ast.unparse(call.func).rsplit(".", 1)[-1] not in RECORDERS:
                continue
            for keyword in call.keywords:
                if keyword.arg == "roles" and isinstance(keyword.value, ast.Dict):
                    used |= {value.id for value in keyword.value.values if isinstance(value, ast.Name) and value.id in keywords}
        if used:
            found[function.name] = {**{position: name for position, name in enumerate(parameters) if name in used}, **{name: name for name in used}}
    return found


def strays(files: dict[Path, str]) -> list[Stray]:
    known = schema()
    found: list[Stray] = []
    for path, text in files.items():
        tree = ast.parse(text)
        flow = Flow(known, role_parameters(tree))
        flow.visit(tree)
        found.extend(Stray(path, line, name, table, sink) for line, name, table, sink in flow.found)
    return found


def main() -> int:
    found = strays({path: path.read_text(encoding="utf-8") for path in sorted(SOURCE.rglob("*.py"))})
    for item in found:
        where = f"{item.path.relative_to(ROOT)}:{item.line}"
        print(f"{where}: {item.name} is an id of {item.table}, which names no node, yet it is passed as {item.sink}; pass the node it belongs to")
    print(f"non-node ids passed as nodes: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
