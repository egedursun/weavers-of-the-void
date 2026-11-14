import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
READERS = (SOURCE / "services" / "books", SOURCE / "services" / "codex.py", SOURCE / "services" / "search.py", SOURCE / "services" / "player", SOURCE / "api")
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


def cuts(files: dict[Path, str]) -> list[Cut]:
    found: list[Cut] = []
    for path, text in files.items():
        for number, line in enumerate(text.splitlines(), start=1):
            found.extend(Cut(path, number, reason) for pattern, reason in CUTS if pattern.search(line))
    return found


def readers() -> dict[Path, str]:
    paths: list[Path] = []
    for reader in READERS:
        paths.extend(sorted(reader.rglob("*.py")) if reader.is_dir() else [reader])
    return {path: path.read_text(encoding="utf-8") for path in paths}


def main() -> int:
    found = cuts(readers())
    for item in found:
        print(f"{item.path.relative_to(ROOT)}:{item.line}: a reader of the chronicle {item.reason}")
    print(f"record cuts: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
