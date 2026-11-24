import argparse
import dataclasses
import os
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

from aerona.constants.app import APP_NAME
from aerona.core.grammar import singular
from aerona.engine.interconnect.catalog import REGISTERED
from aerona.rules.constraints import ASCENDING_CHAINS
from aerona.rules.model import EPOCH_YEARS, RuleDescriptor, Spanned, rule_meta
from aerona.rules.registry import Rules
from aerona.rules.snapshot import catalog

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "docs" / "game-rules.md"
SIGNATURE = f'[booklet]: # "{APP_NAME} booklet: the rules of the world"'
PERCENT_SUFFIX = "_pct"
ANCHOR = re.compile(r'<a id="([^"]+)"></a>')
LINK = re.compile(r"\]\(#([^)]+)\)")


def slug(prefix: str, value: str) -> str:
    return f"{prefix}-{re.sub(r'[^a-z0-9_-]+', '-', value.lower()).strip('-')}"


def plain(text: str) -> str:
    words = text.replace("_", " ").strip()
    return words[:1].upper() + words[1:]


def sentence(text: str) -> str:
    text = text.strip().replace("|", "\\|").replace("\n", " ").replace("_", " ")
    return text[:1].upper() + text[1:] if text else text


def count(number: int, one: str, many: str) -> str:
    return f"{number:,} {one if number == 1 else many}"


def amount(value: float) -> str:
    return f"{value:,}" if isinstance(value, int) else f"{value:,.6g}"


class Booklet:
    def __init__(self) -> None:
        rules = Rules()
        self.descriptors = catalog(rules)
        self.by_path = {descriptor.path: descriptor for descriptor in self.descriptors}
        self.parts = {definition.name: getattr(rules, definition.name) for definition in dataclasses.fields(rules)}
        self.units = {
            f"{namespace}.{definition.name}": rule_meta(definition).unit for namespace, part in self.parts.items() for definition in dataclasses.fields(part)
        }
        self.tied: dict[str, set[str]] = defaultdict(set)
        for mechanic in REGISTERED.values():
            for coupling in mechanic.couplings:
                if coupling.rule_key in self.by_path:
                    self.tied[coupling.rule_key].add(mechanic.title)
        self.chains: dict[str, int] = {}
        for position, chain in enumerate(ASCENDING_CHAINS, start=1):
            for path in chain.paths:
                self.chains.setdefault(path, position)
        self.groups: dict[str, dict[str, list[RuleDescriptor]]] = {}
        for descriptor in self.descriptors:
            self.groups.setdefault(str(descriptor.group), {}).setdefault(descriptor.namespace, []).append(descriptor)

    def with_unit(self, descriptor: RuleDescriptor, value: float) -> str:
        unit = self.units.get(descriptor.path, "")
        if unit:
            return f"{amount(value)} {unit if value != 1 else singular(unit)}"
        if descriptor.key.endswith(PERCENT_SUFFIX):
            return f"{amount(value)}%"
        return amount(value)

    def name_of(self, path: str) -> str:
        descriptor = self.by_path.get(path)
        if descriptor is None:
            return plain(path.rpartition(".")[2])
        return f"[{sentence(descriptor.label)}](#{slug('r', path)})"

    def lines(self) -> list[str]:
        return [SIGNATURE, "", *self.opening(), *self.contents(), *self.how_to_read(), *self.overview(), *self.chapters(), *self.ordering()]

    def opening(self) -> list[str]:
        timed = sum(1 for unit in self.units.values() if unit)
        topics = sum(len(namespaces) for namespaces in self.groups.values())
        return [
            f"# {APP_NAME}: The Rules of the World",
            "",
            "Every world runs on a book of rules: how fast peoples grow, how often wars break out, how long a curse lingers, "
            "how far a god's hand can reach. This booklet lists every one of them with the value a new world starts from and the range "
            "it may take. You can change any of them for your own world from World rules in the settings.",
            "",
            "| The rule book at a glance | |",
            "|---|---:|",
            f"| Rules | {len(self.descriptors):,} |",
            f"| Chapters | {len(self.groups):,} |",
            f"| Topics | {topics:,} |",
            f"| Rules counted in years | {timed:,} |",
            f"| Rules tied to a named mechanic | {len(self.tied):,} |",
            f"| Sets of rules that must stay in order | {len(ASCENDING_CHAINS):,} |",
            "",
        ]

    def contents(self) -> list[str]:
        return [
            "## Contents",
            "",
            "1. [How to read this booklet](#how-to-read-this-booklet)",
            "2. [The chapters](#the-chapters)",
            "3. [The rules, chapter by chapter](#the-rules-chapter-by-chapter)",
            *(
                f"   - [{sentence(group)}](#{slug('g', group)}) ({sum(len(items) for items in namespaces.values()):,})"
                for group, namespaces in self.groups.items()
            ),
            "4. [Rules that must stay in order](#rules-that-must-stay-in-order)",
            "",
        ]

    def how_to_read(self) -> list[str]:
        return [
            "## How to read this booklet",
            "",
            "- The rules are gathered into **chapters** and, within each chapter, into **topics**, in the same order as World rules in the settings.",
            "- **Starts at** is the value every new world begins with.",
            "- **Range** runs from the lowest value the rule accepts to the highest value advised. You may go above the advised highest value; "
            "the game warns you but lets the world run. You may not go below the lowest.",
            f"- An epoch lasts {EPOCH_YEARS} years unless your world says otherwise. Rules counted in years follow your world's epoch length.",
            "- **Tied to** names the mechanics of the world that this rule governs directly. "
            "The companion booklet *How the World Connects* describes each of them.",
            "- A rule marked **in order** belongs to a set whose values must rise from one to the next; the last chapter lists those sets.",
            "",
        ]

    def overview(self) -> list[str]:
        lines = ["## The chapters", "", "| Chapter | Topics | Rules |", "|---|---:|---:|"]
        for group, namespaces in self.groups.items():
            lines.append(f"| [{sentence(group)}](#{slug('g', group)}) | {len(namespaces):,} | {sum(len(items) for items in namespaces.values()):,} |")
        return [*lines, ""]

    def chapters(self) -> list[str]:
        lines = ["## The rules, chapter by chapter", ""]
        for group, namespaces in self.groups.items():
            total = sum(len(items) for items in namespaces.values())
            topics = ", ".join(plain(name).lower() for name in namespaces)
            lines += [
                f'<a id="{slug("g", group)}"></a>',
                "",
                f"### {sentence(group)}",
                "",
                f"{count(total, 'rule', 'rules')} in {count(len(namespaces), 'topic', 'topics')}: {topics}.",
                "",
            ]
            for namespace, descriptors in namespaces.items():
                lines += self.topic(namespace, descriptors)
        return lines

    def topic(self, namespace: str, descriptors: list[RuleDescriptor]) -> list[str]:
        lines = [f"#### {plain(namespace)}", ""]
        if isinstance(self.parts[namespace], Spanned) and any(self.units.get(item.path) for item in descriptors):
            lines += ["The rules counted in years here follow your world's epoch length.", ""]
        lines += ["| Rule | Starts at | Range | Tied to |", "|---|---:|---|---|"]
        for descriptor in descriptors:
            lines.append(self.row(descriptor))
        return [*lines, ""]

    def row(self, descriptor: RuleDescriptor) -> str:
        path = descriptor.path
        label = sentence(descriptor.label)
        if path in self.chains:
            label += f" *(in order: [set {self.chains[path]}](#rules-that-must-stay-in-order))*"
        tied = "; ".join(sentence(title) for title in sorted(self.tied.get(path, ()))) or "—"
        span = f"{self.with_unit(descriptor, descriptor.minimum)} to {self.with_unit(descriptor, descriptor.maximum)}"
        return f'| <a id="{slug("r", path)}"></a>{label} | {self.with_unit(descriptor, descriptor.default)} | {span} | {tied} |'

    def ordering(self) -> list[str]:
        lines = [
            "## Rules that must stay in order",
            "",
            "In each set below, every rule must be at least as large as the one before it. In a strict set, each must be larger.",
            "",
            "| Set | Rules, from lowest to highest | Kind |",
            "|---:|---|---|",
        ]
        for position, chain in enumerate(ASCENDING_CHAINS, start=1):
            kind = "strict" if chain.strict else "may be equal"
            lines.append(f"| {position} | {' → '.join(self.name_of(path) for path in chain.paths)} | {kind} |")
        return [*lines, ""]


def broken_links(text: str) -> list[str]:
    anchors = set(ANCHOR.findall(text))
    headings = {re.sub(r"[^a-z0-9 -]", "", line.lstrip("#").strip().lower()).replace(" ", "-") for line in text.splitlines() if line.startswith("## ")}
    return sorted({target for target in LINK.findall(text) if target not in anchors and target not in headings})


def missing_entries(text: str) -> list[str]:
    anchors = set(ANCHOR.findall(text))
    return sorted({slug("r", descriptor.path) for descriptor in catalog(Rules())} - anchors)


def ours(path: Path) -> bool:
    if not path.exists():
        return True
    with path.open(encoding="utf-8") as handle:
        return handle.readline().strip() == SIGNATURE


def write_atomically(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the booklet of every game rule, as one Markdown file.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT, help=f"Markdown file to write (default: {DEFAULT_OUTPUT.relative_to(ROOT)})")
    parser.add_argument("--stdout", action="store_true", help="print the Markdown instead of writing a file")
    parser.add_argument("--force", action="store_true", help="replace an existing file that this script did not write")
    arguments = parser.parse_args()
    text = "\n".join(Booklet().lines()).rstrip() + "\n"
    problems = [f"broken link #{target}" for target in broken_links(text)] + [f"missing entry #{anchor}" for anchor in missing_entries(text)]
    if problems:
        print("The booklet is incomplete, nothing was written:", *problems, sep="\n  ", file=sys.stderr)
        return 1
    if arguments.stdout:
        sys.stdout.write(text)
        return 0
    output = arguments.out.resolve()
    if not arguments.force and not ours(output):
        print(f"{output} exists and was not written by this script; pass --force or choose another --out.", file=sys.stderr)
        return 2
    write_atomically(output, text)
    print(f"Wrote {output} ({len(text.encode('utf-8')) / 1_048_576:.1f} MB, {count(len(catalog(Rules())), 'rule', 'rules')}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
