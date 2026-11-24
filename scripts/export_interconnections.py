import argparse
import math
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict
from enum import Enum
from pathlib import Path

from aerona.constants.app import APP_NAME
from aerona.engine.interconnect.annotations import declared_reads, declared_writes
from aerona.engine.interconnect.catalog import REGISTERED
from aerona.engine.interconnect.edges import GENERIC_CARRIERS, INFRASTRUCTURE, declared_edges, modifier_edges
from aerona.engine.interconnect.explorer import affects_by_writer, flow_index, subsystem_links
from aerona.engine.interconnect.registry import Edge, EdgeKind, Mechanic, Subsystem
from aerona.engine.pipeline import all_phases

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "docs" / "interconnections.md"
SIGNATURE = f'[booklet]: # "{APP_NAME} booklet: how the world connects"'
PART_NAMES = {Subsystem.SOCIAL: "Society"}
KIND_VERBS = {
    EdgeKind.FLOW: "Passes on to",
    EdgeKind.MODIFIER: "Bends",
    EdgeKind.TRIGGER: "Sets off events in",
    EdgeKind.RULE_SWITCH: "Turns on or off in",
}
KIND_MEANINGS = {
    EdgeKind.FLOW: "what one part produces, another part takes up.",
    EdgeKind.MODIFIER: "one part raises or lowers a value that another part relies on, for as long as the cause lasts.",
    EdgeKind.TRIGGER: "something that happens in one part sets something in motion in another.",
    EdgeKind.RULE_SWITCH: "a world rule decides whether this connection works at all.",
}
TOP_PARTS = 3
FOLD_AT = 24
HEAT = ("·", "●", "●●", "●●●")
ANCHOR = re.compile(r'<a id="([^"]+)"></a>')
LINK = re.compile(r"\]\(#([^)]+)\)")


def slug(prefix: str, value: str) -> str:
    return f"{prefix}-{re.sub(r'[^a-z0-9_-]+', '-', value.lower()).strip('-')}"


def plain(value: Enum | str) -> str:
    text = value.value if isinstance(value, Enum) else value
    words = text.split(".", 1)[-1] if text.startswith("table.") else text
    words = words.replace("_", " ").replace(".", " ").strip()
    return words[:1].upper() + words[1:]


def part(subsystem: Subsystem) -> str:
    return PART_NAMES.get(subsystem, plain(subsystem))


def part_link(subsystem: Subsystem) -> str:
    return f"[{part(subsystem)}](#{slug('part', subsystem.value)})"


def clause(text: str) -> str:
    text = sentence(text)
    return text if len(text) > 1 and text[1].isupper() else text[:1].lower() + text[1:]


def sentence(text: str) -> str:
    text = text.strip().replace("|", "\\|").replace("\n", " ")
    if not text:
        return text
    text = text[:1].upper() + text[1:]
    return text if text.endswith((".", "!", "?")) else f"{text}."


def count(number: int, one: str, many: str) -> str:
    return f"{number:,} {one if number == 1 else many}"


def listing(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return f"{', '.join(items[:-1])} and {items[-1]}"


def folded(items: list[str], noun: tuple[str, str], separator: str = " · ") -> list[str]:
    if not items:
        return ["None."]
    if len(items) <= FOLD_AT:
        return [separator.join(items)]
    return ["", "<details>", f"<summary>{count(len(items), *noun)}</summary>", "", separator.join(items), "", "</details>", ""]


def spread(counter: Counter[Subsystem]) -> str:
    if not counter:
        return "none"
    return ", ".join(f"{part(subsystem)} ({number:,})" for subsystem, number in sorted(counter.items(), key=lambda item: (-item[1], item[0].value)))


def mechanic_link(key: str) -> str:
    mechanic = REGISTERED.get(key)
    return f"[{sentence(mechanic.title).rstrip('.')}](#{slug('m', key)})" if mechanic else plain(key)


def heat(edges: int, most: int) -> str:
    if edges <= 0 or most <= 0:
        return HEAT[0]
    share = math.log1p(edges) / math.log1p(most)
    return HEAT[3] if share > 0.75 else HEAT[2] if share > 0.45 else HEAT[1]


class Booklet:
    def __init__(self) -> None:
        self.phases = all_phases()
        self.writes = {phase.name: sorted(declared_writes(phase.run) - INFRASTRUCTURE) for phase in self.phases}
        self.reads = {phase.name: sorted(declared_reads(phase.run) - INFRASTRUCTURE) for phase in self.phases}
        self.index = flow_index()
        self.shared = sorted({key for keys in (*self.writes.values(), *self.reads.values()) for key in keys} - GENERIC_CARRIERS)
        self.links = [link for link in subsystem_links() if link.source is not link.target]
        self.edges = {(link.source, link.target): link.edges for link in self.links}
        self.declared = declared_edges()
        self.affects = affects_by_writer()
        self.by_part: dict[Subsystem, list[Mechanic]] = defaultdict(list)
        self.living: dict[str, list[Mechanic]] = defaultdict(list)
        for mechanic in REGISTERED.values():
            self.by_part[mechanic.subsystem].append(mechanic)
            for name in mechanic.phases:
                self.living[name].append(mechanic)

    def lines(self) -> list[str]:
        return [
            SIGNATURE,
            "",
            *self.opening(),
            *self.contents(),
            *self.how_to_read(),
            *self.parts(),
            *self.grid(),
            *self.chapters(),
            *self.part_to_part(),
            *self.lasting_influences(),
            *self.shared_things(),
            *self.epoch_order(),
        ]

    def opening(self) -> list[str]:
        flows = 0
        for mechanic in REGISTERED.values():
            fed: set[str] = set()
            for key in {item for name in mechanic.phases for item in self.writes.get(name, ())} - GENERIC_CARRIERS:
                fed.update(reader.key for reader in self.index.readers.get(key, ()))
            flows += len(fed - {mechanic.key})
        return [
            f"# {APP_NAME}: How the World Connects",
            "",
            "A guide to the living parts of the world and the ways each one reaches into the others. Nothing in the world happens alone: "
            "a harvest feeds a city, the city raises an army, the army's war empties the granaries, and hunger turns hearts toward new gods. "
            "This booklet follows every one of those paths.",
            "",
            "| The world at a glance | |",
            "|---|---:|",
            f"| Parts of the world | {len(Subsystem):,} |",
            f"| Mechanics (the workings that make the world move) | {len(REGISTERED):,} |",
            f"| Pairs of parts that reach each other | {len(self.links):,} |",
            f"| Connections described in words | {len(self.declared):,} |",
            f"| Things the parts share and pass between them | {len(self.shared):,} |",
            f"| Ways one mechanic feeds another | {flows:,} |",
            f"| Steps in the turn of an epoch | {len(self.phases):,} |",
            "",
        ]

    def contents(self) -> list[str]:
        return [
            "## Contents",
            "",
            "1. [How to read this booklet](#how-to-read-this-booklet)",
            "2. [The parts of the world](#the-parts-of-the-world)",
            "3. [Who shapes whom](#who-shapes-whom)",
            "4. [The mechanics, part by part](#the-mechanics-part-by-part)",
            *(f"   - {part_link(subsystem)} ({len(self.by_part[subsystem]):,})" for subsystem in Subsystem),
            "5. [From one part to another](#from-one-part-to-another)",
            "6. [Lasting influences](#lasting-influences)",
            "7. [What the parts share](#what-the-parts-share)",
            "8. [The turn of an epoch](#the-turn-of-an-epoch)",
            "",
        ]

    def how_to_read(self) -> list[str]:
        return [
            "## How to read this booklet",
            "",
            "- The world is divided into **parts**: the body, the mind, society, the economy, faith, war, the cosmos and more.",
            "- Each part holds **mechanics**. A mechanic is one working of the world, described in a sentence: what happens, to whom, and why.",
            "- Mechanics reach beyond their own part in four ways:",
            *(f"  - **{plain(kind)}**: {KIND_MEANINGS.get(kind, 'one part reaches another.')}" for kind in EdgeKind),
            "- Every mechanic below lists the parts it reaches, the parts it draws on, what it acts upon, and the actions your sons and mortals "
            "can take on it.",
            "- The world moves in **epochs** of fifty years. In each epoch every step runs once, in the order given at the end of this booklet.",
            "",
        ]

    def parts(self) -> list[str]:
        lines = [
            "## The parts of the world",
            "",
            "| Part | Mechanics | Shapes most | Shaped most by |",
            "|---|---:|---|---|",
        ]
        for subsystem in Subsystem:
            shapes = sorted(((target, edges) for (source, target), edges in self.edges.items() if source is subsystem), key=lambda item: -item[1])
            shaped = sorted(((source, edges) for (source, target), edges in self.edges.items() if target is subsystem), key=lambda item: -item[1])
            lines.append(
                f"| {part_link(subsystem)} | {len(self.by_part[subsystem]):,} | {', '.join(part(item) for item, _ in shapes[:TOP_PARTS]) or '—'} "
                f"| {', '.join(part(item) for item, _ in shaped[:TOP_PARTS]) or '—'} |"
            )
        return [*lines, ""]

    def grid(self) -> list[str]:
        subsystems = list(Subsystem)
        most = max(self.edges.values(), default=0)
        lines = [
            "## Who shapes whom",
            "",
            f"Read across a row to see how strongly that part shapes each other part: {HEAT[3]} strongly, {HEAT[2]} clearly, {HEAT[1]} a little, "
            f"{HEAT[0]} not at all.",
            "",
            "| Shapes → | " + " | ".join(part(subsystem) for subsystem in subsystems) + " |",
            "|---|" + ":---:|" * len(subsystems),
        ]
        for source in subsystems:
            row = ["—" if source is target else heat(self.edges.get((source, target), 0), most) for target in subsystems]
            lines.append(f"| **{part(source)}** | " + " | ".join(row) + " |")
        return [*lines, ""]

    def chapters(self) -> list[str]:
        lines = ["## The mechanics, part by part", ""]
        for subsystem in Subsystem:
            mechanics = sorted(self.by_part[subsystem], key=lambda item: item.title.lower())
            reaches = sorted((target for (source, target) in self.edges if source is subsystem), key=lambda item: -self.edges[(subsystem, item)])
            lines += [
                f'<a id="{slug("part", subsystem.value)}"></a>',
                "",
                f"### {part(subsystem)}",
                "",
                f"{count(len(mechanics), 'mechanic', 'mechanics')}. {part(subsystem)} reaches {listing([part(item) for item in reaches]) or 'no other part'}.",
                "",
            ]
            for mechanic in mechanics:
                lines += self.mechanic(mechanic)
        return lines

    def mechanic(self, mechanic: Mechanic) -> list[str]:
        lines = [f'<a id="{slug("m", mechanic.key)}"></a>', "", f"#### {sentence(mechanic.title).rstrip('.')}", ""]
        for coupling in mechanic.couplings:
            verb = KIND_VERBS.get(coupling.kind, "Reaches")
            lines.append(f"- **{verb} {part(coupling.target)}:** {clause(coupling.carrier)}")
        if mechanic.couplings:
            lines.append("")
        facts = []
        reaches = sorted(self.affects.get(mechanic.key, frozenset()) - {mechanic.subsystem}, key=lambda item: item.value)
        if reaches:
            facts.append(f"Its effects reach {self.parts_named(mechanic, reaches)}.")
        draws = sorted(self.draws_on(mechanic) - {mechanic.subsystem}, key=lambda item: item.value)
        if draws:
            facts.append(f"It draws on {self.parts_named(mechanic, draws)}.")
        if mechanic.targets:
            facts.append(f"It acts on: {', '.join(plain(item).lower() for item in mechanic.targets)}.")
        if mechanic.tools:
            facts.append(f"Sons and mortals can act on it: {listing([plain(item).lower() for item in mechanic.tools])}.")
        if mechanic.isolated_reason:
            facts.append(sentence(mechanic.isolated_reason))
        if facts:
            lines += [" ".join(facts), ""]
        return lines

    @staticmethod
    def parts_named(mechanic: Mechanic, found: list[Subsystem]) -> str:
        if set(found) >= set(Subsystem) - {mechanic.subsystem}:
            return "every other part of the world"
        return listing([part(item) for item in found])

    def draws_on(self, mechanic: Mechanic) -> set[Subsystem]:
        found: set[Subsystem] = set()
        for key in {item for name in mechanic.phases for item in self.reads.get(name, ())} - GENERIC_CARRIERS:
            found.update(writer.subsystem for writer in self.index.writers.get(key, ()) if writer.key != mechanic.key)
        return found

    def part_to_part(self) -> list[str]:
        lines = ["## From one part to another", "", "Every connection described in words, gathered by the two parts it joins.", ""]
        grouped: dict[tuple[Subsystem, Subsystem], list[Edge]] = defaultdict(list)
        for edge in self.declared:
            grouped[(edge.source, edge.target)].append(edge)
        order = list(Subsystem)
        for (source, target), edges in sorted(grouped.items(), key=lambda item: (order.index(item[0][0]), order.index(item[0][1]))):
            title = f"Within {part(source)}" if source is target else f"{part(source)} → {part(target)}"
            lines += [f"### {title}", ""]
            for edge in sorted(edges, key=lambda item: (REGISTERED[item.writer].title.lower() if item.writer in REGISTERED else item.writer, item.carrier)):
                lines.append(f"- {sentence(edge.carrier)} *{plain(edge.kind)}, from {mechanic_link(edge.writer)}.*")
            lines.append("")
        return lines

    def lasting_influences(self) -> list[str]:
        grouped: dict[tuple[Subsystem, str, str], set[str]] = defaultdict(set)
        for edge in modifier_edges():
            source = (edge.rule_key or "").rpartition(".")[2]
            grouped[(edge.source, source, edge.carrier)].add(edge.reader or "")
        lines = [
            "## Lasting influences",
            "",
            "Some causes keep bending a value for as long as they last: a wound weakens, a blessing lifts, a law taxes. "
            "Each row names the cause, the value it bends and the mechanics that feel it.",
            "",
            "| From | Cause | Bends | Mechanics that feel it | Their parts |",
            "|---|---|---|---:|---|",
        ]
        order = list(Subsystem)
        for (subsystem, source, carrier), readers in sorted(grouped.items(), key=lambda item: (order.index(item[0][0]), item[0][1], item[0][2])):
            parts = Counter(REGISTERED[key].subsystem for key in readers if key in REGISTERED)
            lines.append(f"| {part(subsystem)} | {plain(source)} | {plain(carrier).lower()} | {len(readers):,} | {spread(parts)} |")
        return [*lines, ""]

    def shared_things(self) -> list[str]:
        lines = [
            "## What the parts share",
            "",
            "The parts of the world speak to each other through the things they keep: herds and harvests, armies and their morale, "
            "faiths and their followers. For each thing, the parts that change it and the parts that use it.",
            "",
            "| Thing | Changed by | Used by |",
            "|---|---|---|",
        ]
        for key in sorted(self.shared, key=lambda item: plain(item).lower()):
            changed = Counter(mechanic.subsystem for mechanic in self.index.writers.get(key, ()))
            used = Counter(mechanic.subsystem for mechanic in self.index.readers.get(key, ()))
            lines.append(f"| {plain(key)} | {spread(changed)} | {spread(used)} |")
        return [*lines, ""]

    def epoch_order(self) -> list[str]:
        lines = [
            "## The turn of an epoch",
            "",
            "Every epoch, the world takes these steps in this order. Each step names the mechanics at work in it and the things it changes.",
            "",
        ]
        for position, phase in enumerate(self.phases, start=1):
            living = sorted(self.living.get(phase.name, []), key=lambda item: item.title.lower())
            changed = [plain(key).lower() for key in self.writes[phase.name] if key not in GENERIC_CARRIERS]
            lines += [f"### {position}. {plain(phase.name)}", ""]
            if living:
                lines += ["**Mechanics at work:** ", *folded([mechanic_link(mechanic.key) for mechanic in living], ("mechanic", "mechanics")), ""]
            if changed:
                lines += ["**Changes:** ", *folded(changed, ("thing", "things"), ", "), ""]
            if not living and not changed:
                lines += ["Keeps the world's records in order.", ""]
        return lines


def broken_links(text: str) -> list[str]:
    anchors = set(ANCHOR.findall(text))
    headings = {re.sub(r"[^a-z0-9 -]", "", line.lstrip("#").strip().lower()).replace(" ", "-") for line in text.splitlines() if line.startswith("## ")}
    return sorted({target for target in LINK.findall(text) if target not in anchors and target not in headings})


def missing_entries(text: str) -> list[str]:
    anchors = set(ANCHOR.findall(text))
    expected = {slug("m", key) for key in REGISTERED} | {slug("part", subsystem.value) for subsystem in Subsystem}
    return sorted(expected - anchors)


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
    parser = argparse.ArgumentParser(description="Write the booklet of how the world's parts connect, as one Markdown file.")
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
    print(f"Wrote {output} ({len(text.encode('utf-8')) / 1_048_576:.1f} MB, {count(len(REGISTERED), 'mechanic', 'mechanics')}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
