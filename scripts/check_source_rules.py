import ast
import io
import re
import sys
import tokenize
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
TURKISH_ALLOWED_FILES = frozenset({Path("backend/src/aerona/migration/legacy/schema_map.json")})
PROMPT_HOME = Path("backend/src/aerona/prompts")
PROMPT_MARKERS = re.compile(r"\b(you are|your task|respond with|return only|write a|as the narrator)\b", re.IGNORECASE)
PROMPT_WORD_LIMIT = 40
PROSE_ALLOWED = (PROMPT_HOME, Path("backend/src/aerona/catalog"), Path("backend/src/aerona/rules"), Path("backend/tests"), Path("scripts"))


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    rule: str

    def render(self) -> str:
        return f"{self.path}:{self.line}: {self.rule}"


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


def python_violations(path: Path, text: str) -> list[Violation]:
    found: list[Violation] = []
    relative = path.relative_to(ROOT)
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, SyntaxError):
        return [Violation(relative, 1, "unparseable python")]
    for token in tokens:
        if token.type == tokenize.COMMENT:
            found.append(Violation(relative, token.start[0], "comment"))
    tree = ast.parse(text)
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
    elif suffix in HASH_COMMENT_SUFFIXES or path.name in HASH_COMMENT_NAMES or path.name.startswith(".env"):
        found.extend(Violation(relative, number, "comment") for number in hash_comment_lines(text))
    return found


def main() -> int:
    violations = [violation for path in iter_files() for violation in check_file(path)]
    for violation in violations:
        print(violation.render())
    print(f"source rules: {len(violations)} violation(s)")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
