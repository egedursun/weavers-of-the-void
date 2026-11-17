import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from aerona.main import create_app

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_SOURCE = ROOT / "frontend" / "src"
SKIPPED_PARTS = frozenset({"generated", "node_modules"})
SOURCE_SUFFIXES = frozenset({".ts", ".tsx"})
TEST_MARKERS = (".test.", ".spec.")
HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete", "head"})
CLIENT_CALL = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE|HEAD)\(\s*['\"`](/api/[^'\"`]+)['\"`]")
URL_LITERAL = re.compile(r"['\"`](/api/[^'\"`\s]*)['\"`]")
TEMPLATE_PART = re.compile(r"\$\{[^}]*\}")
PATH_PARAMETER = re.compile(r"\{[^/}]+\}")
SEGMENT = "[^/]+"


@dataclass(frozen=True)
class Route:
    method: str
    path: str

    @property
    def pattern(self) -> re.Pattern[str]:
        pieces = PATH_PARAMETER.split(self.path)
        return re.compile("^" + SEGMENT.join(re.escape(piece) for piece in pieces) + "$")


@dataclass(frozen=True)
class Caller:
    method: str | None
    path: str
    file: Path


def api_routes() -> list[Route]:
    schema = create_app().openapi()
    routes = [Route(method.upper(), path) for path, operations in schema["paths"].items() for method in operations if method in HTTP_METHODS]
    return sorted(routes, key=lambda route: (route.path, route.method))


def source_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.suffix in SOURCE_SUFFIXES and path.is_file() and not SKIPPED_PARTS & set(path.parts) and not any(marker in path.name for marker in TEST_MARKERS)
    )


def callers_in(text: str, file: Path) -> list[Caller]:
    found = [Caller(method, path, file) for method, path in CLIENT_CALL.findall(text)]
    typed = {caller.path for caller in found}
    for literal in URL_LITERAL.findall(text):
        cleaned = TEMPLATE_PART.sub("x", literal.split("?", 1)[0])
        if literal not in typed:
            found.append(Caller(None, cleaned, file))
    return found


def frontend_callers(root: Path) -> list[Caller]:
    callers: list[Caller] = []
    for file in source_files(root):
        callers.extend(callers_in(file.read_text(encoding="utf-8"), file))
    return callers


def is_called(route: Route, callers: list[Caller]) -> bool:
    for caller in callers:
        if caller.method is not None:
            if caller.method == route.method and caller.path == route.path:
                return True
        elif route.pattern.match(caller.path):
            return True
    return False


def uncalled(routes: list[Route], callers: list[Caller]) -> list[Route]:
    return [route for route in routes if not is_called(route, callers)]


def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(description="List API routes that no frontend module calls.")
    parser.add_argument("--strict", action="store_true", help="exit with status 1 when any route has no caller")
    options = parser.parse_args(arguments)
    routes = api_routes()
    missing = uncalled(routes, frontend_callers(FRONTEND_SOURCE))
    for route in missing:
        print(f"{route.method:6} {route.path}")
    print(f"{len(routes) - len(missing)} of {len(routes)} API routes have a frontend caller; {len(missing)} have none.")
    return 1 if options.strict and missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
