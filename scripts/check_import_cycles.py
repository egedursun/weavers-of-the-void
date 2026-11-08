import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src"
PACKAGE = "aerona"
SKIPPED = frozenset({"alembic"})


def module_names() -> dict[str, Path]:
    found: dict[str, Path] = {}
    for path in sorted((SOURCE / PACKAGE).rglob("*.py")):
        if SKIPPED & set(path.parts):
            continue
        parts = path.relative_to(SOURCE).with_suffix("").parts
        name = ".".join(parts[:-1] if parts[-1] == "__init__" else parts)
        found[name] = path
    return found


def targets(node: ast.stmt, modules: dict[str, Path]) -> set[str]:
    found: set[str] = set()
    if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module and node.module.startswith(PACKAGE):
        for alias in node.names:
            submodule = f"{node.module}.{alias.name}"
            if submodule in modules:
                found.add(submodule)
            elif node.module in modules:
                found.add(node.module)
    elif isinstance(node, ast.Import):
        found |= {alias.name for alias in node.names if alias.name in modules}
    return found


def import_graph(modules: dict[str, Path]) -> dict[str, set[str]]:
    return {name: {target for node in ast.parse(path.read_text(encoding="utf-8")).body for target in targets(node, modules)} for name, path in modules.items()}


def cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    found: list[list[str]] = []
    for start in sorted(graph):
        if start in index:
            continue
        work: list[tuple[str, list[str]]] = [(start, sorted(graph[start]))]
        index[start] = low[start] = len(index)
        stack.append(start)
        on_stack.add(start)
        while work:
            node, pending = work[-1]
            if pending:
                child = pending.pop()
                if child not in index:
                    index[child] = low[child] = len(index)
                    stack.append(child)
                    on_stack.add(child)
                    work.append((child, sorted(graph[child])))
                elif child in on_stack:
                    low[node] = min(low[node], index[child])
                continue
            work.pop()
            if work:
                low[work[-1][0]] = min(low[work[-1][0]], low[node])
            if low[node] == index[node]:
                component: list[str] = []
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    component.append(member)
                    if member == node:
                        break
                if len(component) > 1:
                    found.append(sorted(component))
    return found


def main() -> int:
    found = cycles(import_graph(module_names()))
    for component in found:
        print(f"import cycle: {' -> '.join(component)}; a module in it cannot be imported on its own")
    if found:
        print(f"{len(found)} import cycle(s)")
        return 1
    print("import cycles: none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
