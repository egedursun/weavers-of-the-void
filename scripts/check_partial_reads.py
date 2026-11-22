import ast
import importlib
import pkgutil
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "backend" / "src" / "aerona"
SKIPPED = ("aerona.db.alembic", "aerona.migration", "aerona.services.books.pdf_worker")
EXITS = (ast.Return, ast.Continue, ast.Raise, ast.Break)

PROVEN: dict[tuple[str, str, str], str] = {
    (
        "api/routers/map.py",
        "STOCK_KEYS",
        "entity.entity_type",
    ): "canon() returns only entities of the types listed in STOCK_KEYS",
    (
        "catalog/zones.py",
        "BASE_ZONES",
        "base",
    ): "ACTS_AS maps each kind to a base kind, and ZONE_OF_STRUCTURE is built with total() at import, so a base outside BASE_ZONES fails at import",
    (
        "engine/collective/dating.py",
        "HOLDER_KINDS",
        "holder.entity_type",
    ): "seed_dating is only given holders from the query filtered to HOLDER_KINDS",
    (
        "engine/communication/post.py",
        "SPEED_RULES",
        "medium",
    ): "instant media return early and NETWORK falls back to LETTER, so only the overland and signal media reach the read",
    (
        "engine/economy/household.py",
        "FUEL_HEAT",
        "kind",
    ): "cost() is only called on fuels drawn from FUEL_FAMILY without fuel and timber, which all have a FUEL_HEAT rule",
    (
        "engine/environment/works.py",
        "STRUCTURE_WORKS",
        "item.profile.kind",
    ): "working() is given the kinds of STRUCTURE_WORKS and returns only structures of those kinds",
    (
        "engine/industry/stores.py",
        "PERISHABLE",
        "lot.commodity",
    ): "perishables() reads only lots of the commodities in PERISHABLE",
    (
        "engine/lore/control.py",
        "PROFILES",
        "entity.entity_type",
    ): "record_of() raises for any type outside PROFILES",
    (
        "engine/lore/rumours.py",
        "CHANCES",
        "channel",
    ): "channels come from Carriers.of(), which yields only the five channels in CHANCES",
    (
        "engine/mortal/acts.py",
        "CAREER_ROLES",
        "path",
    ): "the only caller returns before a STAY path reaches career_role",
    (
        "engine/phases/births.py",
        "RULER_TITLES",
        "community.entity_type",
    ): "crown() is only reached with communities of COMMUNITY_TYPES, the keys of RULER_TITLES",
    (
        "engine/phases/production.py",
        "SPECIES_GROUNDS",
        "commodity",
    ): "without a material the good comes from SPECIES_GOODS, whose goods all have a SPECIES_GROUNDS word",
    (
        "engine/phases/travel.py",
        "LOSS_TEXT",
        "kind",
    ): "kinds come from MEDIUM_EVENTS, PIRATES or COMMON_EVENTS, which all have texts",
    (
        "engine/phases/travel.py",
        "ROAD_EVENT_TEXT",
        "kind",
    ): "kinds come from METHOD_EVENTS, PIRATES or COMMON_EVENTS, which all have texts",
    (
        "engine/polity/offices.py",
        "OFFICE_SKILLS",
        "office",
    ): "staffed offices come from wanted_offices and power skills name offices of the table; the ruler and the heir are never scored",
    (
        "engine/regime/book.py",
        "TYPE_LABELS",
        "kind",
    ): "kinds_of() returns exactly the three types in TYPE_LABELS",
    (
        "engine/transform/cosmos.py",
        "POCKET_WORLDS",
        "profile.kind",
    ): "detach runs only after check(), which refuses a kind outside POCKET_WORLDS",
    (
        "engine/transform/run.py",
        "WARNINGS",
        "row.kind",
    ): "warn runs only for kinds in WARNED_KINDS, the keys of WARNINGS",
    (
        "engine/transform/run.py",
        "KINDS",
        "kind",
    ): "watch runs from the loop over KINDS and perform only after force() refuses kinds outside KINDS",
    (
        "epoch/context.py",
        "PHASE_NAMES",
        "phase",
    ): "enter_phase is only entered with a running phase; NOT_STARTED is the state before any phase",
}


@dataclass(frozen=True)
class PartialRead:
    path: str
    line: int
    table: str
    key: str
    missing: int


@dataclass(frozen=True)
class Table:
    keys: frozenset[Enum]
    missing: frozenset[Enum]


def partial_tables(namespace: Mapping[str, object]) -> dict[str, Table]:
    found: dict[str, Table] = {}
    for name, value in namespace.items():
        if not name.isupper() or not isinstance(value, Mapping) or not value:
            continue
        keys = list(value)
        kind = type(keys[0])
        if not isinstance(keys[0], Enum) or any(type(key) is not kind for key in keys):
            continue
        missing = frozenset(member for member in kind if member not in value)
        if missing:
            found[name] = Table(frozenset(keys), missing)
    return found


def value_of(node: ast.AST, namespace: Mapping[str, object]) -> object:
    if isinstance(node, ast.Name):
        return namespace.get(node.id)
    if isinstance(node, ast.Attribute):
        owner = value_of(node.value, namespace)
        return getattr(owner, node.attr, None) if owner is not None else None
    return None


def members(node: ast.AST, namespace: Mapping[str, object]) -> set[Enum]:
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return {value for element in node.elts if isinstance(value := value_of(element, namespace), Enum)}
    value = value_of(node, namespace)
    if isinstance(value, Enum):
        return {value}
    if isinstance(value, (Mapping, set, frozenset, tuple, list)):
        return {item for item in value if isinstance(item, Enum)}
    return set()


@dataclass
class Known:
    out: set[Enum]
    kept: set[Enum] | None

    def join(self, other: "Known") -> "Known":
        kept = other.kept if self.kept is None else self.kept if other.kept is None else self.kept & other.kept
        return Known(self.out | other.out, kept)


NOTHING_KNOWN = Known(set(), None)
POSITIVE = (ast.Is, ast.Eq, ast.In)
NEGATIVE = (ast.IsNot, ast.NotEq, ast.NotIn)


def known_when(test: ast.AST, key: str, truth: bool, namespace: Mapping[str, object]) -> Known:
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        return known_when(test.operand, key, not truth, namespace)
    if isinstance(test, ast.BoolOp):
        if isinstance(test.op, ast.And) is truth:
            known = Known(set(), None)
            for value in test.values:
                known = known.join(known_when(value, key, truth, namespace))
            return known
        return NOTHING_KNOWN
    if isinstance(test, ast.Compare) and len(test.ops) == 1 and ast.unparse(test.left) == key:
        found = members(test.comparators[0], namespace)
        if not found:
            return NOTHING_KNOWN
        if isinstance(test.ops[0], POSITIVE):
            return Known(set(), found) if truth else Known(found, None)
        if isinstance(test.ops[0], NEGATIVE):
            return Known(found, None) if truth else Known(set(), found)
    return NOTHING_KNOWN


def enums_in(value: object) -> set[Enum]:
    if isinstance(value, Enum):
        return {value}
    if isinstance(value, (set, frozenset, tuple, list)):
        return {item for item in value if isinstance(item, Enum)}
    return set()


def looked_up(node: ast.AST, namespace: Mapping[str, object]) -> set[Enum]:
    if isinstance(node, ast.Subscript):
        table = value_of(node.value, namespace)
        if isinstance(table, Mapping):
            return set().union(*(enums_in(value) for value in table.values()))
    return set()


def iterated(iterable: ast.AST, namespace: Mapping[str, object]) -> set[Enum]:
    if (
        isinstance(iterable, ast.Call)
        and isinstance(iterable.func, ast.Name)
        and iterable.func.id in ("sorted", "list", "tuple", "set", "frozenset", "reversed")
        and iterable.args
    ):
        return iterated(iterable.args[0], namespace)
    if isinstance(iterable, ast.Call) and isinstance(iterable.func, ast.Attribute) and iterable.func.attr in ("keys", "items"):
        return members(iterable.func.value, namespace)
    if isinstance(iterable, ast.GeneratorExp) and len(iterable.generators) == 1:
        return iterated(iterable.generators[0].iter, namespace)
    return members(iterable, namespace) or looked_up(iterable, namespace)


def assigned(value: ast.AST, namespace: Mapping[str, object]) -> set[Enum]:
    if isinstance(value, ast.IfExp):
        body, orelse = (
            assigned(value.body, namespace),
            assigned(value.orelse, namespace),
        )
        return body | orelse if body and orelse else set()
    if isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute) and value.func.attr == "pick" and value.args:
        return iterated(value.args[0], namespace)
    constant = value_of(value, namespace)
    if isinstance(constant, Enum):
        return {constant}
    return looked_up(value, namespace)


def target_key(target: ast.AST) -> str:
    if isinstance(target, ast.Tuple) and target.elts:
        return ast.unparse(target.elts[0])
    return ast.unparse(target)


def last_assignment(block: list[ast.stmt], before: int, key: str) -> ast.AST | None:
    for statement in reversed(block[:before]):
        if isinstance(statement, ast.Assign) and any(ast.unparse(target) == key for target in statement.targets):
            return statement.value
        if isinstance(statement, ast.AnnAssign) and ast.unparse(statement.target) == key:
            return statement.value
    return None


def names_in(node: ast.AST) -> set[str]:
    return {child.id for child in ast.walk(node) if isinstance(child, ast.Name)}


WRAPPERS = ("sorted", "list", "tuple", "set", "frozenset", "reversed", "enumerate")


def filtered(expression: ast.AST, names: frozenset[str]) -> bool:
    return any(
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "in_"
        and any(names & names_in(argument) for argument in call.args)
        for call in ast.walk(expression)
    )


def root_name(node: ast.AST) -> str | None:
    while isinstance(node, (ast.Attribute, ast.Subscript, ast.Call)):
        if isinstance(node, ast.Call):
            node = node.args[0] if isinstance(node.func, ast.Name) and node.func.id in WRAPPERS and node.args else node.func
        else:
            node = node.value
    return node.id if isinstance(node, ast.Name) else None


def aliases(table: Table, name: str, namespace: Mapping[str, object]) -> frozenset[str]:
    found = {name}
    for other, value in namespace.items():
        if other.isupper():
            enums = set(value) if isinstance(value, Mapping) and all(isinstance(key, Enum) for key in value) else enums_in(value)
            if enums and enums <= table.keys:
                found.add(other)
    return frozenset(found)


def bound_names(target: ast.AST) -> set[str]:
    return {child.id for child in ast.walk(target) if isinstance(child, ast.Name)}


def filtered_name(scope: ast.AST | None, name: str | None, table: frozenset[str]) -> bool:
    if scope is None or name is None:
        return False
    for statement in ast.walk(scope):
        if isinstance(statement, ast.Assign) and any(name in bound_names(target) for target in statement.targets) and filtered(statement.value, table):
            return True
    return False


def queried(parents: list[ast.AST], node: ast.Subscript, table: frozenset[str]) -> bool:
    scope = next(
        (parent for parent in reversed(parents) if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef))),
        None,
    )
    name = root_name(node.slice)
    if filtered_name(scope, name, table):
        return True
    for parent in parents:
        loops: list[tuple[ast.AST, ast.AST]] = []
        if isinstance(parent, (ast.For, ast.AsyncFor)):
            loops.append((parent.target, parent.iter))
        if isinstance(parent, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            loops.extend((generator.target, generator.iter) for generator in parent.generators)
        for target, iterable in loops:
            if name in bound_names(target) and (filtered(iterable, table) or filtered_name(scope, root_name(iterable), table)):
                return True
    return False


def excluded(
    parents: list[ast.AST],
    node: ast.Subscript,
    table: Table,
    namespace: Mapping[str, object],
) -> bool:
    key = ast.unparse(node.slice)
    constant = value_of(node.slice, namespace)
    if isinstance(constant, Enum):
        return constant in table.keys
    chain = [*parents, node]
    known = Known(set(), None)
    for index, parent in enumerate(parents):
        child = chain[index + 1]
        if isinstance(parent, (ast.If, ast.IfExp, ast.While)):
            body = parent.body if isinstance(parent.body, list) else [parent.body]
            orelse = parent.orelse if isinstance(parent.orelse, list) else [parent.orelse]
            if child in body:
                known = known.join(known_when(parent.test, key, True, namespace))
            elif child in orelse:
                known = known.join(known_when(parent.test, key, False, namespace))
        if isinstance(parent, ast.BoolOp) and child in parent.values:
            truth = isinstance(parent.op, ast.And)
            for value in parent.values[: parent.values.index(child)]:
                known = known.join(known_when(value, key, truth, namespace))
        if isinstance(parent, (ast.For, ast.AsyncFor)) and child in parent.body and target_key(parent.target) == key:
            known = known.join(Known(set(), iterated(parent.iter, namespace) or None))
        if isinstance(parent, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            for generator in parent.generators:
                if target_key(generator.target) == key:
                    known = known.join(Known(set(), iterated(generator.iter, namespace) or None))
                for test in generator.ifs:
                    known = known.join(known_when(test, key, True, namespace))
        for field in ("body", "orelse", "finalbody"):
            block = getattr(parent, field, None)
            if isinstance(block, list) and child in block:
                position = block.index(child)
                value = last_assignment(block, position, key)
                if value is not None:
                    known = known.join(Known(set(), assigned(value, namespace) or None))
                for statement in block[:position]:
                    if isinstance(statement, ast.If) and statement.body and isinstance(statement.body[-1], EXITS):
                        known = known.join(known_when(statement.test, key, False, namespace))
    return (known.kept is not None and known.kept <= table.keys) or table.missing <= known.out


def reads_in(
    path: Path,
    tables: dict[str, Table],
    namespace: Mapping[str, object],
    proven: Mapping[tuple[str, str, str], str],
    used: set[tuple[str, str, str]],
) -> list[PartialRead]:
    relative = str(path.relative_to(PACKAGE)) if path.is_relative_to(PACKAGE) else path.name
    found: list[PartialRead] = []

    def visit(node: ast.AST, parents: list[ast.AST]) -> None:
        if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load) and isinstance(node.value, ast.Name) and node.value.id in tables:
            table, key = node.value.id, ast.unparse(node.slice)
            if not excluded(parents, node, tables[table], namespace) and not queried(parents, node, aliases(tables[table], table, namespace)):
                if (relative, table, key) in proven:
                    used.add((relative, table, key))
                else:
                    found.append(
                        PartialRead(
                            relative,
                            node.lineno,
                            table,
                            key,
                            len(tables[table].missing),
                        )
                    )
        for child in ast.iter_child_nodes(node):
            visit(child, [*parents, node])

    visit(ast.parse(path.read_text(encoding="utf-8")), [])
    return found


def partial_reads(used: set[tuple[str, str, str]]) -> list[PartialRead]:
    sys.path.insert(0, str(PACKAGE.parent))
    found: list[PartialRead] = []
    for info in pkgutil.walk_packages([str(PACKAGE)], "aerona."):
        if info.name.startswith(SKIPPED):
            continue
        module = importlib.import_module(info.name)
        source = getattr(module, "__file__", None)
        if source is None or not source.endswith(".py"):
            continue
        tables = partial_tables(vars(module))
        if tables:
            found.extend(reads_in(Path(source), tables, vars(module), PROVEN, used))
    return found


def main() -> int:
    used: set[tuple[str, str, str]] = set()
    found = partial_reads(used)
    for read in found:
        print(
            f"{read.path}:{read.line}: {read.table}[{read.key}] reads a table that leaves out {read.missing} value(s) of its enum; make it total, guard the read or use .get"
        )
    stale = sorted(set(PROVEN) - used)
    for path, table, key in stale:
        print(f"{path}: {table}[{key}] is listed as proven but no such unguarded read remains; remove it from PROVEN")
    print(f"partial reads: {len(found) + len(stale)}")
    return 1 if found or stale else 0


if __name__ == "__main__":
    sys.exit(main())
