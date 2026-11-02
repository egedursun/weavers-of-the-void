import argparse
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "docs" / "spec" / "13-depth-expansion.md"
MATRIX = ROOT / "docs" / "spec" / "13-coverage.md"

COLUMNS = ("ID", "Kind", "Title", "Spec", "Module", "Trigger", "Lever", "UI", "LLM", "Templates", "Backfill", "Test", "Status")
WORK_COLUMNS = ("Module", "Trigger", "Lever", "UI", "LLM", "Templates", "Backfill", "Test")
STATUSES = frozenset({"planned", "in-progress", "done", "deferred-approved"})
EMPTY = frozenset({"", "—", "-", "todo"})
TITLE_LIMIT = 120
NOT_APPLICABLE = "n/a"

FOUNDATION_HEADING = re.compile(r"^### (F\d+)\. (.+)$")
FOUNDATION_SUBHEADING = re.compile(r"^#### (F\d+\.\d+) (.+)$")
FOUNDATION_PASS = re.compile(r"^#### (F\d+) reference pass(?: (\d+))?:? ?(.*)$")
SECTION_HEADING = re.compile(r"^### (\d+\.\d+[a-z]?) (.+)$")
DELIVERABLE_HEADING = re.compile(r"^### ((?:I|J)\.\d+[a-z]?) (.+)$")
SECTION_PASS = re.compile(r"^#### Reference pass(?: (\d+))?(?: \((.*)\))?$")
AUDIT_HEADING = re.compile(r"^### (1R\.\d+) (.+)$")
OTHER_HEADING = re.compile(r"^#{2,3} ")
NUMBERED_ROW = re.compile(r"^\| (\d+|C\d+) \| (.+)$")
OCM_ROW = re.compile(r"^\| (\d{2}) \| ([^|]+) \| (◐|—) \|")
LOOP_ROW = re.compile(r"^\| (L\d+) \| [RB] \| ([^|]+) \|")
WAVE_ROW = re.compile(r"^\| (W\d+\+?)(?: \(extended\))? \| ([^|]+) \|")
GROUND_RULE_ROW = re.compile(r"^\| (G\d+) \| ([^|]+) \|")
DECISION_ROW = re.compile(r"^\| (K\.\d+) \| ([^|]+) \|")
STORY_ITEM = re.compile(r"^(\d+)\. \*\*([^*]+)\*\*")
STORY_HEADING = re.compile(r"acceptance stories|stories", re.IGNORECASE)
TYPE_SECTIONS = {"title": "S4.11", "art_form": "S7.5", "art form": "S7.5", "theory": "S8.4b", "8.4b": "S8.4b"}
SUMMARY_HEADING = re.compile(r"totals|convergence|count", re.IGNORECASE)
SHARED_ROW = re.compile(r"\(with (\d{2})\)")
COVERED_ROW = re.compile(r"^\| \d{2} \| [^|]+ \| ● \|")
REFERENCE = re.compile(r"\b(F\d+(?:\.\d+)?|\d+\.\d+[a-z]?|J\.\d+[a-z]?|I\.\d+)(?: (?:RP|reference pass)(?: ?(\d+))?)?\b")


@dataclass
class Item:
    key: str
    kind: str
    title: str
    spec: str
    targets: tuple[str, ...] = ()


@dataclass
class Row:
    values: dict[str, str] = field(default_factory=dict)

    def get(self, column: str) -> str:
        return self.values.get(column, "").strip()


def clean(text: str) -> str:
    return text.replace("|", "/").replace("**", "").strip()


def pass_key(owner: str, number: str | None) -> str:
    return f"{owner}/RP{number or '2'}"


def reference_keys(text: str) -> tuple[str, ...]:
    keys: list[str] = []
    for match in REFERENCE.finditer(text):
        base, number = match.group(1), match.group(2)
        owner = base if base.startswith(("F", "J.", "I.")) else f"S{base}"
        keys.append(pass_key(owner, number) if "RP" in match.group(0) or "reference pass" in match.group(0) else owner)
    if "2T.6" in text:
        keys.extend(section for name, section in TYPE_SECTIONS.items() if name in text)
    return tuple(dict.fromkeys(keys))


class SpecParser:
    def __init__(self) -> None:
        self.items: dict[str, Item] = {}
        self.owner: str | None = None
        self.audit: str | None = None
        self.stories = False
        self.handlers: tuple[tuple[re.Pattern[str], Callable[[re.Match[str], str], None]], ...] = (
            (FOUNDATION_HEADING, self.foundation),
            (DELIVERABLE_HEADING, self.deliverable),
            (SECTION_HEADING, self.section),
            (AUDIT_HEADING, self.audit_section),
            (FOUNDATION_SUBHEADING, self.foundation_part),
            (FOUNDATION_PASS, self.foundation_pass),
            (SECTION_PASS, self.section_pass),
            (LOOP_ROW, self.simple("loop", "Part I")),
            (GROUND_RULE_ROW, self.simple("ground-rule", "Part 0")),
            (DECISION_ROW, self.simple("decision", "Part K")),
            (WAVE_ROW, self.wave),
            (STORY_ITEM, self.story),
            (OCM_ROW, self.ocm_gap),
            (NUMBERED_ROW, self.numbered_gap),
        )

    def add(self, item: Item) -> None:
        self.items.setdefault(item.key, item)

    def parse(self, text: str) -> list[Item]:
        for line in text.splitlines():
            if self.audit and COVERED_ROW.match(line):
                continue
            for pattern, handler in self.handlers:
                if match := pattern.match(line):
                    handler(match, line)
                    break
            else:
                if OTHER_HEADING.match(line) and not line.startswith("####"):
                    self.owner, self.audit, self.stories = None, None, False
        return list(self.items.values())

    def foundation(self, match: re.Match[str], _: str) -> None:
        self.owner, self.audit, self.stories = match.group(1), None, False
        self.add(Item(match.group(1), "foundation", clean(match.group(2)), f"§{match.group(1)}"))

    def deliverable(self, match: re.Match[str], _: str) -> None:
        self.owner, self.audit = match.group(1), None
        self.stories = bool(STORY_HEADING.search(match.group(2)))
        self.add(Item(match.group(1), "deliverable", clean(match.group(2)), f"§{match.group(1)}"))

    def section(self, match: re.Match[str], _: str) -> None:
        self.owner, self.audit, self.stories = f"S{match.group(1)}", None, False
        self.add(Item(self.owner, "section", clean(match.group(2)), f"§{match.group(1)}"))

    def audit_section(self, match: re.Match[str], _: str) -> None:
        self.owner, self.stories = None, False
        self.audit = None if SUMMARY_HEADING.search(match.group(2)) else match.group(1)

    def foundation_part(self, match: re.Match[str], _: str) -> None:
        self.add(Item(match.group(1), "foundation", clean(match.group(2)), f"§{match.group(1)}"))

    def foundation_pass(self, match: re.Match[str], _: str) -> None:
        number = match.group(2) or "2"
        title = clean(match.group(3)) or "reference pass"
        self.add(Item(pass_key(match.group(1), match.group(2)), "reference-pass", title, f"§{match.group(1)} reference pass {number}"))

    def section_pass(self, match: re.Match[str], _: str) -> None:
        if not self.owner or not self.owner.startswith("S"):
            return
        number = match.group(1) or "2"
        title = clean(match.group(2) or "reference pass")
        self.add(Item(pass_key(self.owner, match.group(1)), "reference-pass", title, f"§{self.owner[1:]} reference pass {number}"))

    def simple(self, kind: str, spec: str) -> Callable[[re.Match[str], str], None]:
        def handle(match: re.Match[str], _: str) -> None:
            self.add(Item(match.group(1), kind, clean(match.group(2)), spec))

        return handle

    def wave(self, match: re.Match[str], line: str) -> None:
        if not line.startswith("| Wave"):
            self.add(Item(match.group(1), "wave", clean(match.group(2))[:TITLE_LIMIT], "Part J"))

    def story(self, match: re.Match[str], _: str) -> None:
        if self.stories:
            self.add(Item(f"AS{match.group(1)}", "story", clean(match.group(2)), "Part I"))

    def ocm_gap(self, match: re.Match[str], line: str) -> None:
        if not self.audit:
            return
        resolution = cells_of(line)[-1]
        targets = reference_keys(resolution)
        shared = SHARED_ROW.search(resolution)
        if shared and f"G{self.audit}.{shared.group(1)}" in self.items:
            targets = self.items[f"G{self.audit}.{shared.group(1)}"].targets
        self.add(Item(f"G{self.audit}.{match.group(1)}", "gap", clean(match.group(2)), f"§{self.audit}", targets))

    def numbered_gap(self, match: re.Match[str], line: str) -> None:
        if not self.audit:
            return
        cells = cells_of(line)
        self.add(Item(f"G{self.audit}.{match.group(1)}", "gap", clean(cells[1])[:TITLE_LIMIT], f"§{self.audit}", reference_keys(cells[-1])))


def cells_of(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def parse_spec(text: str) -> list[Item]:
    return SpecParser().parse(text)


def parse_matrix(text: str) -> dict[str, Row]:
    rows: dict[str, Row] = {}
    for line in text.splitlines():
        if not line.startswith("| ") or line.startswith("| ID ") or line.startswith("|---"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != len(COLUMNS):
            continue
        rows[cells[0]] = Row(dict(zip(COLUMNS, cells, strict=True)))
    return rows


def render(items: list[Item], existing: dict[str, Row]) -> str:
    lines = [
        "# Depth expansion coverage matrix",
        "",
        "Traceability matrix for `docs/spec/13-depth-expansion.md` (spec J.19). Generated and checked by `scripts/spec_coverage.py`.",
        "Every numbered item of the spec has one row.",
        "A row is `done` only when every work column is filled (or `n/a` where it does not apply) and its test passes.",
        "`deferred-approved` requires the user's explicit approval and a reason in the Test column.",
        "Gap rows (kind `gap`) are done when every section they point to is done.",
        "Run `python scripts/spec_coverage.py write` after editing the spec, and `python scripts/spec_coverage.py check` to verify.",
        "",
        "| " + " | ".join(COLUMNS) + " |",
        "|" + "|".join("---" for _ in COLUMNS) + "|",
    ]
    for item in items:
        previous = existing.get(item.key)
        values = {column: (previous.get(column) if previous else "") for column in COLUMNS}
        values["ID"], values["Kind"], values["Title"], values["Spec"] = item.key, item.kind, item.title, item.spec
        if item.kind == "gap":
            values["Module"] = "→ " + (", ".join(item.targets) if item.targets else "see spec")
            for column in WORK_COLUMNS[1:]:
                values[column] = values[column] or NOT_APPLICABLE
        for column in WORK_COLUMNS:
            values[column] = values[column] or "—"
        values["Status"] = values["Status"] or "planned"
        lines.append("| " + " | ".join(values[column] for column in COLUMNS) + " |")
    lines.append("")
    return "\n".join(lines)


def check(items: list[Item], rows: dict[str, Row]) -> list[str]:
    problems: list[str] = []
    keys = {item.key for item in items}
    for item in items:
        if item.key not in rows:
            problems.append(f"missing row for {item.key} ({item.title})")
    for key in rows:
        if key not in keys:
            problems.append(f"row {key} has no item in the spec")
    for key, row in rows.items():
        status = row.get("Status")
        if status not in STATUSES:
            problems.append(f"row {key} has an unknown status '{status}'")
        if status == "deferred-approved" and row.get("Test") in EMPTY:
            problems.append(f"row {key} is deferred without a recorded approval and reason")
        if status == "done" and row.get("Kind") != "gap":
            empty = [column for column in WORK_COLUMNS if row.get(column) in EMPTY]
            if empty:
                problems.append(f"row {key} is done but has empty columns: {', '.join(empty)}")
    by_key = {item.key: item for item in items}
    for key, row in rows.items():
        item = by_key.get(key)
        if item is None or item.kind != "gap" or row.get("Status") != "done":
            continue
        open_targets = [target for target in item.targets if rows.get(target, Row()).get("Status") != "done"]
        if open_targets:
            problems.append(f"gap {key} is done but its targets are open: {', '.join(open_targets)}")
    return problems


def summary(rows: dict[str, Row]) -> str:
    counts: dict[str, int] = {}
    for row in rows.values():
        counts[row.get("Status")] = counts.get(row.get("Status"), 0) + 1
    return ", ".join(f"{status}: {count}" for status, count in sorted(counts.items()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("write", "check", "summary"))
    mode = parser.parse_args().mode
    items = parse_spec(SPEC.read_text(encoding="utf-8"))
    existing = parse_matrix(MATRIX.read_text(encoding="utf-8")) if MATRIX.exists() else {}
    if mode == "write":
        MATRIX.write_text(render(items, existing), encoding="utf-8")
        print(f"{len(items)} items written to {MATRIX.relative_to(ROOT)}")
        return 0
    if mode == "summary":
        print(f"{len(existing)} rows. {summary(existing)}")
        return 0
    problems = check(items, existing)
    for problem in problems:
        print(problem)
    print(f"{len(items)} items, {len(problems)} problem(s). {summary(existing)}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
