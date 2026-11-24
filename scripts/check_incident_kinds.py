import argparse
import ast
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from string import Formatter

sys.path.insert(0, str(Path(__file__).resolve().parent))

from incident_sites import SOURCE, Site, write_sites

sys.path.insert(0, str(SOURCE.parent))

from aerona.catalog.incident_kinds.amounts import amount_problems
from aerona.catalog.incident_kinds.phases import PHASE_NAMES
from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.catalog.incident_kinds.spec import IncidentKindSpec

FIELDS = Formatter()
KNOWERS = frozenset({"witness", "teller"})


def placeholders(template: str) -> set[str]:
    return {
        name.split("[")[0].split(".")[0]
        for _, name, _, _ in FIELDS.parse(template)
        if name
    }


def kind_problems(spec: IncidentKindSpec) -> list[str]:
    if not spec.told:
        return []
    found: list[str] = []
    if spec.draft:
        found.append("is still a generated draft")
    if not spec.template.strip():
        found.append("has no template")
    if not spec.roles:
        found.append("declares no roles")
    named = {role.role.value for role in spec.roles} | {fact.key for fact in spec.facts}
    unknown = sorted(placeholders(spec.template) - named)
    if unknown:
        found.append(f"tells {', '.join(unknown)} that it does not declare")
    for fact in spec.facts:
        if fact.value.value == "enum" and fact.enum is None:
            found.append(f"declares the enum fact {fact.key} without its enum")
        if fact.value.value == "number" and fact.unit is None:
            found.append(f"declares the number {fact.key} without its unit")
    return found


def family_of(key: str) -> str:
    return key.split(".", 1)[0]


def site_problems(site: Site) -> list[str]:
    found: list[str] = []
    if site.unresolved:
        found.append(
            f"writes a key the build cannot list ({'; '.join(site.unresolved)[:120]})"
        )
    missing = [key for key in site.keys if key not in INCIDENT_KINDS]
    if missing:
        found.append(f"writes keys with no kind: {', '.join(missing[:6])}")
    if site.rendered:
        found.append("passes a pre-rendered line instead of roles and facts")
    return found


def call_key(node: ast.Call) -> str | None:
    func = node.func
    named = isinstance(func, ast.Name) and func.id == "record"
    method = isinstance(func, ast.Attribute) and func.attr == "record"
    if not (named or method) or not node.args:
        return None
    first = node.args[1] if named and len(node.args) > 1 else node.args[0]
    return (
        first.value
        if isinstance(first, ast.Constant) and isinstance(first.value, str)
        else None
    )


def literal_keys(node: ast.Call, name: str) -> tuple[set[str], bool] | None:
    found = next(
        (keyword.value for keyword in node.keywords if keyword.arg == name), None
    )
    if not isinstance(found, ast.Dict):
        return None
    keys: set[str] = set()
    complete = True
    for key in found.keys:
        if key is None:
            complete = False
        elif isinstance(key, ast.Constant) and isinstance(key.value, str):
            keys.add(key.value)
        elif isinstance(key, ast.Attribute):
            keys.add(key.attr.lower())
        else:
            complete = False
    return keys, complete


NUMBER_CALLS = frozenset(
    {
        "len",
        "round",
        "int",
        "float",
        "sum",
        "round_half_up",
        "clamp_int",
        "max",
        "min",
        "abs",
    }
)


def value_shape(value: ast.expr) -> str | None:
    if isinstance(value, ast.JoinedStr) or (
        isinstance(value, ast.Constant) and isinstance(value.value, str)
    ):
        return "text"
    if isinstance(value, ast.Attribute) and value.attr == "name":
        return "text"
    if (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id == "str"
    ):
        return "text"
    if (
        isinstance(value, ast.Constant)
        and isinstance(value.value, (int, float))
        and not isinstance(value.value, bool)
    ):
        return "number"
    if (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id in NUMBER_CALLS
    ):
        return "number"
    return None


def shape_problems(spec: IncidentKindSpec, node: ast.Call) -> list[str]:
    found = next(
        (keyword.value for keyword in node.keywords if keyword.arg == "facts"), None
    )
    if not isinstance(found, ast.Dict):
        return []
    declared = {fact.key: fact.value.value for fact in spec.facts}
    problems = []
    for key, value in zip(found.keys, found.values, strict=True):
        if (
            not (isinstance(key, ast.Constant) and isinstance(key.value, str))
            or key.value not in declared
        ):
            continue
        shape = value_shape(value)
        kind = declared[key.value]
        if (shape == "text" and kind in {"number", "node"}) or (
            shape == "number" and kind == "name"
        ):
            problems.append(
                f"gives the {kind} fact {key.value} of {spec.key} a {shape}"
            )
    return problems


LIST_CALLS = frozenset({"list", "sorted", "tuple", "set"})


def gives_many(value: ast.expr) -> bool:
    if isinstance(value, (ast.List, ast.ListComp, ast.Set, ast.SetComp, ast.Tuple)):
        return True
    return isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id in LIST_CALLS


def many_problems(spec: IncidentKindSpec, node: ast.Call) -> list[str]:
    found = next((keyword.value for keyword in node.keywords if keyword.arg == "roles"), None)
    if not isinstance(found, ast.Dict):
        return []
    single = {role.role.value for role in spec.roles if not role.many}
    problems = []
    for key, value in zip(found.keys, found.values, strict=True):
        name = key.attr.lower() if isinstance(key, ast.Attribute) else key.value if isinstance(key, ast.Constant) else None
        if name in single and gives_many(value):
            problems.append(f"gives several nodes to the single role {name} of {spec.key}; declare it many")
    return problems


def given_problems(spec: IncidentKindSpec, node: ast.Call) -> list[str]:
    found: list[str] = []
    place = next(
        (keyword.value for keyword in node.keywords if keyword.arg == "place"), None
    )
    if spec.place.value == "required" and (
        place is None or (isinstance(place, ast.Constant) and place.value is None)
    ):
        found.append(f"writes {spec.key}, whose place is required, without a place")
    roles = literal_keys(node, "roles")
    if roles is not None:
        declared = {role.role.value for role in spec.roles} | KNOWERS
        unknown = sorted(roles[0] - declared)
        if unknown:
            found.append(
                f"gives {spec.key} roles it does not declare: {', '.join(unknown)}"
            )
        missing = sorted(
            role.role.value
            for role in spec.roles
            if role.required and role.role.value not in roles[0]
        )
        if roles[1] and missing:
            found.append(
                f"leaves out required roles of {spec.key}: {', '.join(missing)}"
            )
    facts = literal_keys(node, "facts")
    if facts is not None:
        declared = {fact.key for fact in spec.facts}
        unknown = sorted(facts[0] - declared)
        if unknown:
            found.append(
                f"gives {spec.key} facts it does not declare: {', '.join(unknown)}"
            )
        missing = sorted(
            fact.key
            for fact in spec.facts
            if fact.required and fact.key not in facts[0]
        )
        if facts[1] and missing:
            found.append(
                f"leaves out required facts of {spec.key}: {', '.join(missing)}"
            )
    found.extend(shape_problems(spec, node))
    found.extend(many_problems(spec, node))
    return found


def call_problems() -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for path in sorted(SOURCE.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            key = call_key(node)
            spec = INCIDENT_KINDS.get(key) if key is not None else None
            if spec is None:
                continue
            for problem in given_problems(spec, node):
                found.append(
                    (
                        family_of(spec.key),
                        f"{path.relative_to(SOURCE)}:{node.lineno}: {problem}",
                    )
                )
    return found


WRITERS = ("engine", "tools", "services", "agents")


def module_of(path: Path) -> str:
    return ".".join(
        path.resolve().relative_to(SOURCE.resolve().parent).with_suffix("").parts
    )


def built_actions(tree: ast.Module, text: str) -> set[str]:
    aliases = {"StepAction"} | {
        alias.asname
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
        if alias.name == "StepAction" and alias.asname
    }
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for value in [*node.args, *(keyword.value for keyword in node.keywords)]:
                if (
                    isinstance(value, ast.Attribute)
                    and isinstance(value.value, ast.Name)
                    and value.value.id in aliases
                ):
                    found.add(value.attr)
    return found


def step_flow_problems(sites: list[Site]) -> list[str]:
    modules: dict[str, tuple[set[str], set[str], set[str], Path]] = {}
    for base in WRITERS:
        for path in sorted((SOURCE / base).rglob("*.py")):
            text = path.read_text()
            tree = ast.parse(text)
            held_keys = {
                node.value.value
                for node in tree.body
                if isinstance(node, ast.Assign)
                and isinstance(node.value, ast.Constant)
                and node.value.value in INCIDENT_KINDS
            }
            imports = {
                node.module
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module
            }
            modules[module_of(path)] = (
                built_actions(tree, text),
                held_keys,
                imports,
                path,
            )
    for site in sites:
        name = module_of(site.path if site.path.is_absolute() else SOURCE / site.path)
        if name in modules:
            modules[name][1].update(site.keys)
    found: list[str] = []
    for name, (built, keys, imports, path) in sorted(modules.items()):
        if not built:
            continue
        importers: set[str] = set()
        frontier = {name}
        while frontier:
            frontier = (
                {other for other, entry in modules.items() if entry[2] & frontier}
                - importers
                - {name}
            )
            importers |= frontier
        receivers = keys | {
            key
            for other in importers | (imports & set(modules))
            for key in modules[other][1]
        }
        if not receivers:
            continue
        declared = {
            action.name
            for key in receivers
            if key in INCIDENT_KINDS
            for action in INCIDENT_KINDS[key].steps
        }
        missing = sorted(built - declared)
        if missing:
            found.append(
                f"{path.relative_to(SOURCE)}: builds steps no kind it can reach declares: {', '.join(missing)}"
            )
    return found


def appended_helpers(trees: dict[Path, ast.Module]) -> dict[str, str]:
    helpers: dict[str, str] = {}
    for tree in trees.values():
        constants = {
            target.id: node.value.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        for function in ast.walk(tree):
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for node in ast.walk(function):
                if (
                    isinstance(node, ast.Call)
                    and getattr(node.func, "id", None) == "append_steps"
                    and len(node.args) > 2
                ):
                    key = node.args[2]
                    resolved = (
                        constants.get(key.id)
                        if isinstance(key, ast.Name)
                        else key.value
                        if isinstance(key, ast.Constant)
                        else None
                    )
                    if isinstance(resolved, str) and resolved in INCIDENT_KINDS:
                        helpers[function.name] = resolved
    return helpers


def helper_step_problems() -> list[str]:
    trees = {
        path: ast.parse(path.read_text())
        for base in WRITERS
        for path in sorted((SOURCE / base).rglob("*.py"))
    }
    helpers = appended_helpers(trees)
    found: list[str] = []
    for path, tree in trees.items():
        for node in ast.walk(tree):
            if (
                not isinstance(node, ast.Call)
                or getattr(node.func, "id", None) not in helpers
            ):
                continue
            key = helpers[node.func.id]
            declared = {action.name for action in INCIDENT_KINDS[key].steps}
            for value in [*node.args, *(keyword.value for keyword in node.keywords)]:
                if (
                    isinstance(value, ast.Attribute)
                    and isinstance(value.value, ast.Name)
                    and value.value.id == "StepAction"
                    and value.attr not in declared
                ):
                    found.append(
                        f"{path.relative_to(SOURCE)}:{node.lineno}: adds the step {value.attr} to {key}, which does not declare it"
                    )
    return found


def collect(families: set[str] | None) -> dict[str, list[str]]:
    sites = write_sites()
    written = {key for site in sites for key in site.keys}
    problems: dict[str, list[str]] = defaultdict(list)
    for site in sites:
        for problem in site_problems(site):
            family = family_of(site.keys[0]) if site.keys else "unkeyed"
            problems[family].append(f"{site.where}: {problem}")
    for key, spec in INCIDENT_KINDS.items():
        family = family_of(key)
        if spec.told and not spec.legacy and key not in written:
            problems[family].append(f"{key}: is declared but nothing writes it")
        for problem in kind_problems(spec):
            problems[family].append(f"{key}: {problem}")
    for family, line in call_problems():
        problems[family].append(line)
    for line in step_flow_problems(sites):
        problems["step_flow"].append(line)
    for line in helper_step_problems():
        problems["step_flow"].append(line)
    for line in amount_problems(dict(INCIDENT_KINDS)):
        problems[family_of(line.split(":", 1)[0])].append(line)
    from aerona.engine.pipeline import PHASE_REGISTRY

    if set(PHASE_NAMES) != set(PHASE_REGISTRY):
        problems["phase"].append(
            f"phase kinds differ from the engine steps: {sorted(set(PHASE_REGISTRY) ^ set(PHASE_NAMES))[:8]}"
        )
    return {
        family: lines
        for family, lines in problems.items()
        if families is None or family in families
    }


CATALOG = SOURCE / "catalog" / "incident_kinds"
VERSIONS = SOURCE / "db" / "alembic" / "versions"


def catalog_keys(text: str) -> set[str]:
    return {
        node.args[0].value
        for node in ast.walk(ast.parse(text))
        if isinstance(node, ast.Call)
        and getattr(node.func, "id", "") == "IncidentKindSpec"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    }


def shipped_keys(revision: str = "HEAD") -> set[str]:
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, cwd=SOURCE).stdout.strip()
    listed = subprocess.run(["git", "ls-tree", "--name-only", revision, f"{CATALOG.relative_to(root)}/"], capture_output=True, text=True, cwd=root)
    keys: set[str] = set()
    for name in listed.stdout.split():
        if name.endswith(".py"):
            keys |= catalog_keys(subprocess.run(["git", "show", f"{revision}:{name}"], capture_output=True, text=True, cwd=root).stdout)
    return keys


def renamed_kinds(versions: Path = VERSIONS) -> set[str]:
    former: set[str] = set()
    for path in sorted(versions.glob("*.py")):
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "RENAMED_KINDS" for target in node.targets):
                former |= {pair[0] for pair in ast.literal_eval(node.value)}
    return former


def retired_kind_problems(shipped: set[str], current: set[str], renamed: set[str]) -> list[str]:
    return [f"{key}: a shipped incident kind left the catalog without a RENAMED_KINDS migration for stored incidents" for key in sorted(shipped - current - renamed)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--family", action="append", default=None)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    problems = collect(set(args.family) if args.family else None)
    current = set(INCIDENT_KINDS).union(*(catalog_keys(path.read_text(encoding="utf-8")) for path in sorted(CATALOG.glob("*.py"))))
    retired = retired_kind_problems(shipped_keys(), current, renamed_kinds())
    if retired:
        problems["retired"] = retired
    total = sum(len(lines) for lines in problems.values())
    if args.summary:
        for family, lines in sorted(problems.items(), key=lambda item: -len(item[1])):
            print(f"{len(lines):5d} {family}")
    else:
        for family in sorted(problems):
            for line in problems[family]:
                print(line)
    print(f"incident kinds: {len(INCIDENT_KINDS)} kinds, {total} problem(s)")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
