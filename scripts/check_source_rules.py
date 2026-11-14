import ast
import hashlib
import io
import json
import os
import re
import sys
import tempfile
import tokenize
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCANNED_ROOTS = ("backend", "frontend", "image-worker", "deploy", "scripts")
SKIPPED_DIRS = {
    "node_modules",
    ".venv",
    "dist",
    "build",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "coverage",
    ".import_linter_cache",
    ".vite-cache",
}
PYTHON_SUFFIXES = {".py"}
SKIPPED_FILES = {"routeTree.gen.ts", "package-lock.json", "uv.lock"}
SCRIPT_SUFFIXES = {".ts", ".tsx", ".js", ".mjs", ".cjs", ".jsx", ".json"}
STYLE_SUFFIXES = {".css"}
MARKUP_SUFFIXES = {".html", ".j2"}
HASH_COMMENT_SUFFIXES = {".toml", ".yaml", ".yml", ".ini", ".cfg", ".conf", ".sh", ".env", ".example"}
HASH_COMMENT_NAMES = {"Dockerfile", "Makefile", ".gitignore", ".dockerignore"}

TURKISH_CODEPOINTS = (0x011F, 0x011E, 0x0131, 0x0130, 0x015F, 0x015E, 0x00E7, 0x00C7, 0x00F6, 0x00D6, 0x00FC, 0x00DC)
TURKISH_CHARACTERS = re.compile("[" + "".join(chr(code) for code in TURKISH_CODEPOINTS) + "]")
TURKISH_ALLOWED_FILES = frozenset(
    {Path("backend/src/aerona/migration/legacy/schema_map.json"), Path("backend/src/aerona/migration/legacy/backfill_words.json")}
)
PROMPT_HOME = Path("backend/src/aerona/prompts")
PROMPT_MARKERS = re.compile(r"\b(you are|your task|respond with|return only|write a|as the narrator)\b", re.IGNORECASE)
PROMPT_WORD_LIMIT = 40
FIXED_ARTICLE = re.compile(r"(?<![A-Za-z{])[Aa] \{")
ARTICLE_HOME = Path("backend/src")
PROSE_ALLOWED = (PROMPT_HOME, Path("backend/src/aerona/catalog"), Path("backend/src/aerona/rules"), Path("backend/tests"), Path("scripts"))


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    rule: str

    def render(self) -> str:
        return f"{self.path}:{self.line}: {self.rule}"


NAIVE_SINGULAR = re.compile(r"""\.rstrip\(\s*['\"]s['\"]\s*\)""")


def iter_files() -> list[Path]:
    files: list[Path] = []
    for root_name in SCANNED_ROOTS:
        base = ROOT / root_name
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if any(part in SKIPPED_DIRS for part in path.relative_to(ROOT).parts) or path.name in SKIPPED_FILES:
                continue
            files.append(path)
    return sorted(files)


def fixed_article(tokens: list[tokenize.TokenInfo], index: int) -> bool:
    token = tokens[index]
    if token.type == tokenize.STRING:
        return FIXED_ARTICLE.search(token.string) is not None
    if token.type != tokenize.FSTRING_MIDDLE or index + 1 >= len(tokens):
        return False
    following = tokens[index + 1]
    return following.type == tokenize.OP and following.string == "{" and FIXED_ARTICLE.search(token.string + "{") is not None


GUARD_MODULE = "aerona.db.write_guard"
GUARD_NAMES = frozenset({"held", "unheld"})


def guard_imports(tree: ast.Module) -> frozenset[str]:
    names = {alias.asname or alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module == GUARD_MODULE for alias in node.names}
    return frozenset(names & GUARD_NAMES)


def shadowed_guards(tree: ast.Module, guards: frozenset[str]) -> list[tuple[int, str]]:
    found: set[tuple[int, str]] = set()
    for scope in ast.walk(tree):
        if not isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        for node in ast.walk(scope):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store) and node.id in guards:
                found.add((node.lineno, node.id))
            if isinstance(node, ast.arg) and node.arg in guards:
                found.add((node.lineno, node.arg))
    return sorted(found)


def python_violations(path: Path, text: str) -> list[Violation]:
    found: list[Violation] = []
    relative = path.relative_to(ROOT)
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, SyntaxError):
        return [Violation(relative, 1, "unparseable python")]
    for index, token in enumerate(tokens):
        if token.type == tokenize.COMMENT:
            found.append(Violation(relative, token.start[0], "comment"))
        if relative.is_relative_to(ARTICLE_HOME) and fixed_article(tokens, index):
            found.append(Violation(relative, token.start[0], "fixed article before a placeholder; use an(), {name:an} or | an"))
    for number, raw in enumerate(text.splitlines(), start=1):
        if NAIVE_SINGULAR.search(raw):
            found.append(Violation(relative, number, "rstrip('s') strips every trailing s and leaves 'entrie' for 'entries'; use singular() from aerona.core.grammar"))
    tree = ast.parse(text)
    for line, name in shadowed_guards(tree, guard_imports(tree)):
        found.append(Violation(relative, line, f"{name} is bound here and hides the hold guard of the same name; give it a name of its own"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                found.append(Violation(relative, body[0].lineno, "docstring"))
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            found.append(Violation(relative, node.lineno, "bare string statement"))
    if not any(relative.is_relative_to(allowed) for allowed in PROSE_ALLOWED):
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                value = node.value
                if PROMPT_MARKERS.search(value) or len(value.split()) > PROMPT_WORD_LIMIT:
                    found.append(Violation(relative, node.lineno, "prompt-like prose outside prompts/"))
    return found


REGEX_PRECEDERS = frozenset({"", "(", ",", "=", ":", "[", "!", "&", "|", "?", "{", "}", ";"})


class ScriptScanner:
    def __init__(self, text: str) -> None:
        self.text = text
        self.length = len(text)
        self.index = 0
        self.line = 1
        self.quote: str | None = None
        self.template_depth: list[int] = []
        self.brace_depth = 0
        self.previous = ""
        self.comment_lines: list[int] = []

    def peek(self, offset: int = 0) -> str:
        position = self.index + offset
        return self.text[position] if position < self.length else ""

    def scan(self) -> list[int]:
        while self.index < self.length:
            if self.peek() == "\n":
                self.line += 1
            if self.quote:
                self.step_in_string()
            else:
                self.step_in_code()
        return self.comment_lines

    def step_in_string(self) -> None:
        char, following = self.peek(), self.peek(1)
        if char == "\\":
            if following == "\n":
                self.line += 1
            self.index += 2
            return
        if self.quote == "`" and char == "$" and following == "{":
            self.template_depth.append(self.brace_depth)
            self.brace_depth += 1
            self.quote = None
            self.index += 2
            return
        if char == self.quote:
            self.quote = None
        self.index += 1

    def step_in_code(self) -> None:
        char, following = self.peek(), self.peek(1)
        if char in "'\"`":
            self.quote = char
            self.index += 1
            return
        if self.handle_braces(char):
            return
        if char == "/" and following == "/":
            self.skip_line_comment()
            return
        if char == "/" and following == "*":
            self.skip_block_comment()
            return
        if char == "/" and self.previous in REGEX_PRECEDERS and self.skip_regex():
            return
        if not char.isspace():
            self.previous = char
        self.index += 1

    def handle_braces(self, char: str) -> bool:
        if char == "{":
            self.brace_depth += 1
        elif char == "}":
            self.brace_depth -= 1
            if self.template_depth and self.template_depth[-1] == self.brace_depth:
                self.template_depth.pop()
                self.quote = "`"
                self.index += 1
                return True
        return False

    def skip_line_comment(self) -> None:
        self.comment_lines.append(self.line)
        while self.index < self.length and self.text[self.index] != "\n":
            self.index += 1

    def skip_block_comment(self) -> None:
        self.comment_lines.append(self.line)
        end = self.text.find("*/", self.index + 2)
        end = self.length if end < 0 else end + 2
        self.line += self.text.count("\n", self.index, end)
        self.index = end

    def skip_regex(self) -> bool:
        closing = self.index + 1
        in_class = False
        while closing < self.length and self.text[closing] != "\n":
            current = self.text[closing]
            if current == "\\":
                closing += 2
                continue
            if current == "[":
                in_class = True
            elif current == "]":
                in_class = False
            elif current == "/" and not in_class:
                self.index = closing + 1
                self.previous = "regex"
                return True
            closing += 1
        return False


def script_comment_lines(text: str) -> list[int]:
    return ScriptScanner(text).scan()


def style_comment_lines(text: str) -> list[int]:
    return [text.count("\n", 0, match.start()) + 1 for match in re.finditer(r"/\*", text)]


def markup_comment_lines(text: str) -> list[int]:
    pattern = re.compile(r"<!--|\{#")
    return [text.count("\n", 0, match.start()) + 1 for match in pattern.finditer(text)]


def hash_comment_lines(text: str) -> list[int]:
    result: list[int] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if stripped.startswith("#") and not stripped.startswith("#!"):
            result.append(number)
    return result


def check_file(path: Path) -> list[Violation]:
    relative = path.relative_to(ROOT)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    found: list[Violation] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        if relative not in TURKISH_ALLOWED_FILES and TURKISH_CHARACTERS.search(raw):
            found.append(Violation(relative, number, "turkish character"))
    suffix = path.suffix
    if suffix in PYTHON_SUFFIXES:
        found.extend(python_violations(path, text))
    elif suffix in SCRIPT_SUFFIXES:
        found.extend(Violation(relative, number, "comment") for number in script_comment_lines(text))
    elif suffix in STYLE_SUFFIXES:
        found.extend(Violation(relative, number, "comment") for number in style_comment_lines(text))
    elif suffix in MARKUP_SUFFIXES:
        found.extend(Violation(relative, number, "comment") for number in markup_comment_lines(text))
        if relative.is_relative_to(ARTICLE_HOME):
            found.extend(
                Violation(relative, number, "fixed article before a placeholder; use an(), {name:an} or | an")
                for number, raw in enumerate(text.splitlines(), start=1)
                if FIXED_ARTICLE.search(raw)
            )
    elif suffix in HASH_COMMENT_SUFFIXES or path.name in HASH_COMMENT_NAMES or path.name.startswith(".env"):
        found.extend(Violation(relative, number, "comment") for number in hash_comment_lines(text))
    return found


RULES_VERSION = hashlib.sha1(Path(__file__).read_bytes()).hexdigest()
CACHE = Path(tempfile.gettempdir()) / f"aerona-source-rules-{RULES_VERSION[:16]}.json"
PARALLEL_FROM = 64


def cache_key(path: Path) -> str:
    return hashlib.sha1(str(path.relative_to(ROOT)).encode() + b"\0" + path.read_bytes()).hexdigest()


def load_cache() -> dict[str, list[list[object]]]:
    try:
        found = json.loads(CACHE.read_text())
    except (OSError, ValueError):
        return {}
    return found if isinstance(found, dict) else {}


def store_cache(cache: dict[str, list[list[object]]]) -> None:
    staging = CACHE.with_suffix(f".{os.getpid()}.tmp")
    try:
        staging.write_text(json.dumps(cache))
        staging.replace(CACHE)
    except OSError:
        staging.unlink(missing_ok=True)


def checked(path: Path) -> list[list[object]]:
    return [[str(violation.path), violation.line, violation.rule] for violation in check_file(path)]


def main() -> int:
    cache = load_cache()
    files = iter_files()
    keys = {path: cache_key(path) for path in files}
    missing = [path for path in files if keys[path] not in cache]
    if len(missing) >= PARALLEL_FROM:
        with ProcessPoolExecutor() as pool:
            results = list(pool.map(checked, missing, chunksize=32))
    else:
        results = [checked(path) for path in missing]
    for path, result in zip(missing, results, strict=True):
        cache[keys[path]] = result
    if missing:
        store_cache({keys[path]: cache[keys[path]] for path in files})
    violations = [Violation(Path(str(path)), int(str(line)), str(rule)) for file in files for path, line, rule in cache[keys[file]]]
    for violation in violations:
        print(violation.render())
    print(f"source rules: {len(violations)} violation(s)")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
