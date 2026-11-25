import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "frontend" / "src"
SCHEMA = SOURCE / "api" / "generated" / "schema.ts"
HELPER = Path("api") / "url.ts"
SUFFIXES = (".ts", ".tsx")
API = re.compile(r"(?<![\w@.\-])/api(?=[/?#]|$)")
SCHEMA_PATH = re.compile(r"^\s*'(/api/[^']*)': \{", re.MULTILINE)
TYPE_HOLES = re.compile(r"^(string|number|infer\s+\w+)$")
HELPER_CALL = re.compile(r"(?:\bapiUrl|\bapi\.(?:GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS))\(\s*$")
TYPE_INDEX = re.compile(r"\bpaths\[\s*$")
SINK = re.compile(
    r"(?:\b(?:href|src|action|poster)\s*=\s*\{?\s*$)"
    r"|(?:\b(?:EventSource|fetch|sendBeacon|location\.assign|location\.replace|window\.open)\(\s*$)"
    r"|(?:\.open\(\s*[^(),]*,\s*$)"
    r"|(?:\b(?:const|let|var)\s+\w*(?:URL|Url|HREF|Href|PATH|Path|BASE|Base)\w*\s*(?::[^=]+)?=\s*$)"
)


@dataclass(frozen=True)
class Literal:
    start: int
    text: str
    holes: tuple[str, ...]


@dataclass(frozen=True)
class RawUrl:
    path: Path
    line: int
    literal: str
    reason: str


def _string_end(text: str, start: int) -> int | None:
    quote = text[start]
    index = start + 1
    while index < len(text):
        char = text[index]
        if char == "\\":
            index += 2
            continue
        if char == "\n":
            return None
        if char == quote:
            return index
        index += 1
    return None


def _template(text: str, start: int, found: list[Literal]) -> int:
    index = start + 1
    parts: list[str] = []
    holes: list[str] = []
    while index < len(text):
        char = text[index]
        if char == "\\":
            parts.append(text[index : index + 2])
            index += 2
            continue
        if char == "`":
            found.append(Literal(start, "".join(parts), tuple(holes)))
            return index + 1
        if text.startswith("${", index):
            end = _expression(text, index + 2, found)
            holes.append(text[index + 2 : end].strip())
            parts.append("${}")
            index = end + 1
            continue
        parts.append(char)
        index += 1
    return index


def _expression(text: str, start: int, found: list[Literal]) -> int:
    depth = 0
    index = start
    while index < len(text):
        char = text[index]
        if char in "'\"":
            end = _string_end(text, index)
            if end is not None:
                found.append(Literal(index, text[index + 1 : end], ()))
                index = end + 1
                continue
        elif char == "`":
            index = _template(text, index, found)
            continue
        elif char == "{":
            depth += 1
        elif char == "}":
            if depth == 0:
                return index
            depth -= 1
        index += 1
    return index


def literals(text: str) -> list[Literal]:
    found: list[Literal] = []
    index = 0
    while index < len(text):
        char = text[index]
        if text.startswith("//", index) and (index == 0 or text[index - 1] != ":"):
            newline = text.find("\n", index)
            index = len(text) if newline < 0 else newline
            continue
        if text.startswith("/*", index):
            close = text.find("*/", index + 2)
            index = len(text) if close < 0 else close + 2
            continue
        if char in "'\"":
            end = _string_end(text, index)
            if end is not None:
                found.append(Literal(index, text[index + 1 : end], ()))
                index = end + 1
                continue
        elif char == "`":
            index = _template(text, index, found)
            continue
        index += 1
    return found


def schema_paths(schema: Path = SCHEMA) -> frozenset[str]:
    if not schema.exists():
        return frozenset()
    return frozenset(SCHEMA_PATH.findall(schema.read_text(encoding="utf-8")))


def _typed(literal: str, paths: frozenset[str]) -> bool:
    if literal in paths:
        return True
    return literal.endswith("/") and any(path.startswith(literal) and path != literal for path in paths)


def _allowed(before: str, literal: Literal) -> bool:
    if HELPER_CALL.search(before) or TYPE_INDEX.search(before):
        return True
    return bool(literal.holes) and all(TYPE_HOLES.match(hole) for hole in literal.holes)


def judge(before: str, literal: Literal, paths: frozenset[str]) -> str | None:
    if _allowed(before, literal):
        return None
    if literal.holes:
        return "builds an API URL by hand"
    if "?" in literal.text or "#" in literal.text:
        return "builds an API URL with a query by hand"
    if SINK.search(before):
        return "hands a raw API URL to the browser"
    return None if _typed(literal.text, paths) else "is not a typed API path"


def exempt(relative: Path) -> bool:
    name = relative.name
    return (
        relative == HELPER
        or "generated" in relative.parts
        or "test-utils" in relative.parts
        or ".test." in name
        or name.lower().endswith(("fixtures.ts", "fixtures.tsx"))
    )


def findings(root: Path = SOURCE, schema: Path = SCHEMA) -> list[RawUrl]:
    paths = schema_paths(schema)
    found: list[RawUrl] = []
    for path in sorted(root.rglob("*")):
        if path.suffix not in SUFFIXES or not path.is_file() or exempt(path.relative_to(root)):
            continue
        text = path.read_text(encoding="utf-8")
        for literal in literals(text):
            if not API.search(literal.text):
                continue
            line_start = text.rfind("\n", 0, literal.start) + 1
            before = text[max(0, line_start - 200) : literal.start]
            reason = judge(before, literal, paths)
            if reason is not None:
                found.append(RawUrl(path, text.count("\n", 0, literal.start) + 1, literal.text, reason))
    return found


def main() -> int:
    found = findings()
    for item in found:
        print(f"{item.path.relative_to(ROOT)}:{item.line}: '{item.literal}' {item.reason}; build it with apiUrl() from src/api/url.ts so it names the universe")
    print(f"raw api urls: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
