import ast
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
TABLES = SOURCE / "db" / "tables"
NODE_BASE = "NodeRow"


@dataclass(frozen=True)
class Misheld:
    path: Path
    line: int
    text: str
    table: str


def row_classes() -> tuple[set[str], set[str]]:
    bases: dict[str, list[str]] = {}
    for path in sorted(TABLES.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ClassDef):
                bases[node.name] = [ast.unparse(base).rsplit(".", 1)[-1] for base in node.bases]

    def is_node(name: str, seen: frozenset[str] = frozenset()) -> bool:
        if name == NODE_BASE:
            return True
        return name not in seen and any(is_node(base, seen | {name}) for base in bases.get(name, []))

    rows = {name for name in bases if name.endswith("Row")}
    nodes = {name for name in rows if is_node(name)}
    return nodes, rows - nodes


def tables_in(node: ast.AST, plain: set[str]) -> set[str]:
    return {item.id for item in ast.walk(node) if isinstance(item, ast.Name) and item.id in plain}


def bound_names(target: ast.AST) -> Iterator[str]:
    if isinstance(target, ast.Name):
        yield target.id
    elif isinstance(target, ast.Tuple):
        for element in target.elts:
            yield from bound_names(element)


def binding_of(source: ast.AST, plain: set[str], nodes: set[str]) -> str | None:
    found = tables_in(source, plain)
    if len(found) != 1 or tables_in(source, nodes) or isinstance(source, ast.Tuple):
        return None
    table = next(iter(found))
    return table if selects_rows_of(source, table) else None


def bind(scope: dict[str, str | None], targets: list[ast.expr], table: str | None) -> None:
    for target in targets:
        for name in bound_names(target):
            scope[name] = table


def selects_rows_of(source: ast.AST, table: str) -> bool:
    for item in ast.walk(source):
        if not isinstance(item, ast.Call):
            continue
        name = ast.unparse(item.func).rsplit(".", 1)[-1]
        first = item.args[0] if item.args else None
        if isinstance(first, ast.Name) and first.id == table and name in {"select", "get", table}:
            return True
        if name == table:
            return True
    return False


class Scoped(ast.NodeVisitor):
    def __init__(self, plain: set[str], nodes: set[str]) -> None:
        self.plain = plain
        self.nodes = nodes
        self.scopes: list[dict[str, str | None]] = [{}]
        self.found: list[tuple[ast.Call, str]] = []

    def visit(self, node: ast.AST) -> None:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            self.enter_function(node)
        elif isinstance(node, ast.For | ast.AsyncFor):
            self.enter_loop(node)
        elif isinstance(node, ast.ListComp | ast.SetComp | ast.GeneratorExp | ast.DictComp):
            self.enter_comprehension(node)
        else:
            super().visit(node)

    def table_of(self, name: str) -> str | None:
        return next((scope[name] for scope in reversed(self.scopes) if name in scope), None)

    def enter_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.scopes.append({})
        for argument in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]:
            found = tables_in(argument.annotation, self.plain) if argument.annotation is not None else set()
            if len(found) == 1 and not tables_in(argument.annotation, self.nodes):
                self.scopes[-1][argument.arg] = next(iter(found))
        self.generic_visit(node)
        self.scopes.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        self.generic_visit(node)
        bind(self.scopes[-1], node.targets, binding_of(node.value, self.plain, self.nodes))

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self.generic_visit(node)
        if node.value is not None:
            bind(self.scopes[-1], [node.target], binding_of(node.value, self.plain, self.nodes))

    def enter_loop(self, node: ast.For | ast.AsyncFor) -> None:
        self.visit(node.iter)
        bind(self.scopes[-1], [node.target], binding_of(node.iter, self.plain, self.nodes))
        for statement in [*node.body, *node.orelse]:
            self.visit(statement)

    def enter_comprehension(self, node: ast.ListComp | ast.SetComp | ast.GeneratorExp | ast.DictComp) -> None:
        self.scopes.append({})
        for generator in node.generators:
            self.visit(generator.iter)
            bind(self.scopes[-1], [generator.target], binding_of(generator.iter, self.plain, self.nodes))
            for condition in generator.ifs:
                self.visit(condition)
        for part in (node.key, node.value) if isinstance(node, ast.DictComp) else (node.elt,):
            self.visit(part)
        self.scopes.pop()

    def visit_Call(self, node: ast.Call) -> None:
        self.generic_visit(node)
        if not isinstance(node.func, ast.Name):
            return
        if node.func.id == "held":
            for argument in node.args:
                if isinstance(argument, ast.Attribute) and argument.attr == "id" and isinstance(argument.value, ast.Name):
                    table = self.table_of(argument.value.id)
                    if table is not None:
                        self.found.append((node, table))
        if node.func.id == "unheld" and node.args:
            argument = node.args[0]
            table = self.table_of(argument.id) if isinstance(argument, ast.Name) else binding_of(argument, self.plain, self.nodes)
            if table is not None:
                self.found.append((node, table))


def misheld_in(tree: ast.AST, plain: set[str], nodes: set[str]) -> list[tuple[ast.Call, str]]:
    visitor = Scoped(plain, nodes)
    visitor.visit(tree)
    return visitor.found


def misheld(files: dict[Path, str]) -> list[Misheld]:
    nodes, plain = row_classes()
    return [Misheld(path, call.lineno, ast.unparse(call), table) for path, text in files.items() for call, table in misheld_in(ast.parse(text), plain, nodes)]


def main() -> int:
    found = misheld({path: path.read_text(encoding="utf-8") for path in sorted(SOURCE.rglob("*.py"))})
    for item in found:
        print(
            f"{item.path.relative_to(ROOT)}:{item.line}: {item.text} asks the hold guard about a {item.table} id, which names no node; ask about the node it belongs to"
        )
    print(f"hold checks on non-node ids: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
