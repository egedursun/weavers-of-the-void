import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPECS = (
    ROOT / "docs" / "spec" / "13-depth-expansion.md",
    ROOT / "docs" / "spec" / "16-minds-powers-living-craft.md",
)
HEADING = re.compile(r"^(#{2,5}) (.+?)\s*$")
NUMBER = r"(?:F\d+(?:\.\d+)*[a-z]?|\d+[a-z]?(?:\.\d+[a-z]?)+|\d+[a-z]?(?=\.\s)|[A-Z]\.\d+)"
NUMBERED = re.compile(rf"^({NUMBER})\.?\s+(?:({NUMBER})\.?\s+)?")
SIDE_PASS = re.compile(r"reference pass", re.IGNORECASE)
POINTER = re.compile(rf"\b{NUMBER}\b")
FACETS: dict[str, tuple[str, ...]] = {
    "typed attributes or tables": (
        "**state",
        "attributes",
        "**model",
        "table",
        "typed",
        "enum",
        "column",
        "profile",
        "catalog",
        "record",
        "`",
    ),
    "behaviours": (
        "behaviour",
        "behavior",
        "**loops",
        "\n1. ",
        "phase",
        "each epoch",
        "reads",
        "engine",
        "incidents",
    ),
    "rules namespace": (
        "rules namespace",
        "rule namespace",
        "rules `",
        "**rules",
        "rules.",
        "`rules",
        "namespace",
        "rule ",
        "rules:",
    ),
    "levers and surfaces": (
        "lever",
        "tools and control",
        "son tool",
        "mortal tool",
        "drawer",
        "surface",
        "player levers",
        "god control",
        "control panel",
        "screen",
        "**tools",
        "thingsections",
    ),
}
COMPLETE_BY_NATURE: dict[str, str] = {
    "0": "ground rules and notation",
    "1": "the baseline of what existed before the expansion",
    "1R": "a reference audit pass whose findings live in the design sections",
    "2T": "a taxonomy review whose results live in the type sections",
    "47.0": "scope and the audit behind it",
    "47.9": "this guard",
    "47.11": "the compliance catalogue, a table of pointers to the sections",
    "47.12": "decisions",
    "5": "delivery rules that every wave of spec 16 follows",
    "50.21": "a sweep of two fixed lists whose findings are built in 50.22 to 50.29",
    "I": "the interconnection registry, a catalogue of couplings and loops that point at their sections",
    "J": "integration notes and summaries that point at their sections",
    "6": "reference lanes whose findings live in the design sections",
}
RANGE = re.compile(rf"({NUMBER})\s*[\u2013-]\s*({NUMBER})")
CATALOGUE = re.compile(r"compliance catalogue|integration of every family", re.IGNORECASE)
EXEMPT_TITLES = (
    "decisions?",
    "totals?",
    "notation",
    "method",
    "measurement",
    "baseline",
    "acceptance stories",
    "scope",
    "audit",
    "glossary",
    "sign-off",
    "order of work",
    "index",
    "guards?",
    "ledger",
    "depth metric",
    "counting rules",
    "self-review",
    "reference lanes",
    "compliance catalogue",
    "couplings, loops and acceptance stories",
    "verification",
    "every mechanic coupled",
    "every node type at its depth target",
    "every value defined",
    "one concept, one taxonomy",
    "cross-cutting layers",
    "surfaces",
    "legacy",
)
TITLE_EXEMPT = re.compile(rf"\b({'|'.join(EXEMPT_TITLES)})\b", re.IGNORECASE)


@dataclass
class Section:
    path: Path
    line: int
    level: int
    title: str
    number: str
    target: str | None
    own: list[str] = field(default_factory=list)
    children: list["Section"] = field(default_factory=list)
    merged: list[str] = field(default_factory=list)


def parse(path: Path) -> list[Section]:
    roots: list[Section] = []
    stack: list[Section] = []
    current: Section | None = None
    for index, line in enumerate(path.read_text().splitlines(), start=1):
        heading = HEADING.match(line)
        if heading is not None:
            level, title = len(heading.group(1)), heading.group(2)
            while stack and stack[-1].level >= level:
                stack.pop()
            numbered = NUMBERED.match(title + " ")
            if numbered is not None and not SIDE_PASS.search(title):
                section = Section(path, index, level, title, numbered.group(1), numbered.group(2))
                if stack:
                    stack[-1].children.append(section)
                else:
                    roots.append(section)
                stack.append(section)
                current = section
                continue
            if level <= 2:
                stack.clear()
                current = None
                continue
        if current is not None:
            current.own.append(line)
    return roots


def family(number: str) -> str:
    return number.split(".", maxsplit=1)[0] if "." in number else number


def walk(section: Section) -> list[Section]:
    return [section, *(item for child in section.children for item in walk(child))]


def gather(roots: list[Section]) -> dict[str, Section]:
    known: dict[str, Section] = {}
    for root in roots:
        for section in walk(root):
            known.setdefault(section.number, section)
    for root in roots:
        for section in walk(root):
            if section is root:
                continue
            home = known.get(section.target) if section.target is not None else None
            if home is None and known.get(section.number) is not section:
                home = known.get(section.number)
            if home is not None and home is not section:
                home.merged.extend(section.own)
                section.own = []
    return known


def expand(cell: str) -> set[str]:
    found = set(POINTER.findall(cell))
    for first, last in RANGE.findall(cell):
        head, _, start = first.rpartition(".")
        tail = last.rpartition(".")[2]
        if head and start.isdigit() and tail.isdigit() and last.rpartition(".")[0] in {head, ""}:
            found |= {f"{head}.{step}" for step in range(int(start), int(tail) + 1)}
    return found


def catalogued(paths: tuple[Path, ...], roots: list[Section]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    rows: dict[str, list[str]] = {}
    for path in paths:
        header = ""
        for line in path.read_text().splitlines():
            if not line.startswith("|"):
                header = ""
                continue
            if line.startswith("|---"):
                continue
            cells = line.strip("|").split("|")
            if not header:
                header = line
                continue
            for number in expand(cells[0]):
                rows.setdefault(number, []).extend([header, line])
    families: dict[str, list[str]] = {}
    for root in roots:
        if CATALOGUE.search(root.title):
            families.setdefault(family(root.number), []).extend(line for line in text_of(root).splitlines() if line.startswith("**"))
    return rows, families


ROWS: dict[str, list[str]] = {}
FAMILIES: dict[str, list[str]] = {}


def text_of(section: Section) -> str:
    named = ROWS.get(section.number, [])
    shared = FAMILIES.get(family(section.number), []) if named else []
    return "\n".join(
        [
            *section.own,
            *section.merged,
            *named,
            *shared,
            *(text_of(child) for child in section.children),
        ]
    )


def exempt(section: Section) -> str | None:
    for number, reason in COMPLETE_BY_NATURE.items():
        if section.number == number or family(section.number) == number:
            return reason
    if TITLE_EXEMPT.search(section.title):
        return "complete by its nature"
    if section.children and not text_of(section).strip():
        return "a container whose parts complete other sections"
    return None


def missing(section: Section) -> list[str]:
    body = text_of(section)
    text = body.lower()
    gaps = [facet for facet, words in FACETS.items() if not any(word in text for word in words)]
    pointed = bool(POINTER.search(body))
    return [] if pointed and len(gaps) <= 1 else gaps


def main() -> int:
    roots = [root for path in SPECS for root in parse(path)]
    gather(roots)
    rows, families = catalogued(SPECS, roots)
    ROWS.update(rows)
    FAMILIES.update(families)
    failures = 0
    for root in roots:
        if exempt(root) is not None:
            continue
        gaps = missing(root)
        if gaps:
            failures += 1
            print(f"{root.path.relative_to(ROOT)}:{root.line}: {root.title} names no {', '.join(gaps)}")
    print(f"spec depth: {failures} thin section(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
