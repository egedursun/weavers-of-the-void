import ast
import re
import tomllib
from importlib.metadata import packages_distributions
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
SOURCE = BACKEND / "src" / "aerona"
NAME = re.compile(r"^[A-Za-z0-9._-]+")


def normal(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def requirement_names(requirements: list[str]) -> set[str]:
    return {normal(match.group(0)) for requirement in requirements if (match := NAME.match(requirement))}


def development_only_modules() -> set[str]:
    project = tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))
    runtime = requirement_names(project["project"]["dependencies"])
    development = requirement_names(project["dependency-groups"]["dev"])
    found: set[str] = set()
    for module, distributions in packages_distributions().items():
        names = {normal(distribution) for distribution in distributions}
        from_development = any(name == wanted or name.startswith(f"{wanted}-") for name in names for wanted in development)
        if from_development and not names & runtime:
            found.add(module)
    return found


def checks_types(node: ast.If) -> bool:
    test = node.test
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING")


def runtime_imports(tree: ast.Module) -> list[ast.Import | ast.ImportFrom]:
    found: list[ast.Import | ast.ImportFrom] = []
    waiting: list[ast.AST] = [tree]
    while waiting:
        node = waiting.pop()
        if isinstance(node, ast.If) and checks_types(node):
            waiting.extend(node.orelse)
            continue
        if isinstance(node, ast.Import | ast.ImportFrom):
            found.append(node)
        waiting.extend(ast.iter_child_nodes(node))
    return found


def top_modules(node: ast.Import | ast.ImportFrom) -> list[str]:
    if isinstance(node, ast.ImportFrom):
        return [node.module.split(".")[0]] if node.module and node.level == 0 else []
    return [alias.name.split(".")[0] for alias in node.names]


def test_the_development_tools_are_known() -> None:
    assert {"pytest", "mypy", "types_aiobotocore_s3"} <= development_only_modules()


def test_no_module_loads_a_development_only_package_at_run_time() -> None:
    forbidden = development_only_modules()
    found = [
        f"{path.relative_to(SOURCE)}:{node.lineno}: {module}"
        for path in sorted(SOURCE.rglob("*.py"))
        for node in runtime_imports(ast.parse(path.read_text(encoding="utf-8")))
        for module in top_modules(node)
        if module in forbidden
    ]
    assert not found, found
