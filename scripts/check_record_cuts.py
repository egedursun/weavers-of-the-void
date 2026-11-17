import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
WRITERS = (SOURCE / "engine", SOURCE / "services", SOURCE / "agents", SOURCE / "tools", SOURCE / "api")
FIXED_CUT = re.compile(r"\[:[0-9]{2,}\]")
READERS = (
    SOURCE / "services" / "books",
    SOURCE / "services" / "codex.py",
    SOURCE / "services" / "search.py",
    SOURCE / "services" / "player",
    SOURCE / "api",
    SOURCE / "prompts",
    SOURCE / "agents" / "context",
    SOURCE / "engine" / "recording" / "accounts.py",
    SOURCE / "engine" / "recording" / "then.py",
    SOURCE / "engine" / "recording" / "search.py",
)
RECORD_ROWS = r"(?:IncidentRow|IncidentParticipantRow|IncidentFactRow|IncidentStepRow|IncidentStepStateRow|IncidentTermRow|StateChangeRow|StateChangeTermRow|ChronicleRow|RumourRow)"
RECORD_SELECT = re.compile(rf"select\({RECORD_ROWS}\b")
RECORD_KIND_DROP = re.compile(r"IncidentRow\.kind\s*(?:!=|\.not_in\(|\.not_like\(|\.notlike\()")
RECORD_SLICE = re.compile(r"\b(?:incidents|accounts|facts|steps|changes|witnesses|rumours|records|history|lines)\b\s*\[\s*(?::\s*[^\]\s]|-[^\]:]+:\s*\])")
CUTS = (
    (
        re.compile(r"ChronicleRow\.visible\b"),
        "filters chronicle lines by visibility, which drops the lines the engine folded; use shown_lines(), or feed_lines() for the feed that shows a fold in their place",
    ),
    (re.compile(r"(!=|is not)\s*ChronicleKind\.ENGINE_RAW\b"), "drops the lines the engine folded; use kept_lines()"),
    (re.compile(r"not_in\([^)]*ChronicleKind\.ENGINE_RAW"), "drops the lines the engine folded; use kept_lines()"),
)


@dataclass(frozen=True)
class Cut:
    path: Path
    line: int
    reason: str


LIMIT_REASON = "limits the records it reads without paging them; page with offset and a show-more, or read them all"


def single_row(call: ast.Call) -> bool:
    return len(call.args) == 1 and isinstance(call.args[0], ast.Constant) and call.args[0].value == 1


def limited_reads(text: str) -> list[int]:
    found: list[int] = []
    for node in ast.walk(ast.parse(text)):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "limit") or single_row(node):
            continue
        chain = ast.unparse(node.func.value)
        if RECORD_SELECT.search(chain) and ".offset(" not in chain:
            found.append(node.lineno)
    return found


def record_cuts(line: str) -> list[str]:
    found: list[str] = []
    if RECORD_KIND_DROP.search(line):
        found.append("drops happenings by their kind; every kind is kept and shown")
    if RECORD_SLICE.search(line):
        found.append("slices the records it read, so the rest are lost; page them or keep them all")
    return found


def cuts(files: dict[Path, str]) -> list[Cut]:
    found: list[Cut] = []
    for path, text in files.items():
        for number, line in enumerate(text.splitlines(), start=1):
            found.extend(Cut(path, number, reason) for pattern, reason in CUTS if pattern.search(line))
            found.extend(Cut(path, number, reason) for reason in record_cuts(line))
        found.extend(Cut(path, number, LIMIT_REASON) for number in limited_reads(text))
    return found


def fixed_cuts(files: dict[Path, str]) -> list[Cut]:
    return [
        Cut(path, number, "cuts what it stores at a fixed length, so the record and the book lose the rest; store it whole")
        for path, text in files.items()
        for number, line in enumerate(text.splitlines(), start=1)
        if FIXED_CUT.search(line)
    ]


def writers() -> dict[Path, str]:
    return {path: path.read_text(encoding="utf-8") for folder in WRITERS for path in sorted(folder.rglob("*.py"))}


def readers() -> dict[Path, str]:
    paths: list[Path] = []
    for reader in READERS:
        paths.extend(sorted(reader.rglob("*.py")) if reader.is_dir() else [reader])
    return {path: path.read_text(encoding="utf-8") for path in paths}


def main() -> int:
    found = cuts(readers())
    for item in found:
        print(f"{item.path.relative_to(ROOT)}:{item.line}: a reader of the chronicle {item.reason}")
    stored = fixed_cuts(writers())
    for item in stored:
        print(f"{item.path.relative_to(ROOT)}:{item.line}: a writer {item.reason}")
    found = found + stored
    print(f"record cuts: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
