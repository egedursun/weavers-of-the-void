import argparse
import enum
import importlib
import json
import os
import pkgutil
import re
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any

import aerona.catalog
from aerona.catalog.climate import CLIMATES
from aerona.catalog.cosmography import (
    APOCALYPSE_LABELS,
    BEING_KINDS,
    CLUSTER_KINDS,
    DIMENSION_KINDS,
    DIMENSIONAL_EVENT_LABELS,
    GALACTIC_EVENT_LABELS,
    GALACTIC_ZONES,
    GALAXY_TYPES,
    PHENOMENON_KINDS,
    STRUCTURE_KINDS,
)
from aerona.catalog.effect_packages import PACKAGES
from aerona.catalog.entity_types import ENTITY_TYPES, EntityTypeSpec
from aerona.catalog.stars import STAR_TYPES
from aerona.catalog.worlds import WORLD_TYPES
from aerona.constants.app import APP_NAME
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.node import NodeKind
from aerona.rules.registry import Rules

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "docs" / "mechanics" / "world-terms.md"
TERMS = ROOT / "docs" / "mechanics" / "world-terms.json"
GLOSSARY = ROOT / "frontend" / "src" / "features" / "help" / "glossary.ts"
TOOLS = "agent-tools.md"
SIGNATURE = f'[booklet]: # "{APP_NAME} booklet: the things of the world and their names"'
ANCHOR = re.compile(r'<a id="([^"]+)"></a>')
LINK = re.compile(r"\]\(#([^)]+)\)")
APP_TERM = re.compile(r"term:\s*'([^']*)',\s*meaning:\s*'([^']*)'", re.DOTALL)
NODE_NAMES = {
    NodeKind.ENTITY: "Thing",
    NodeKind.SON: "Son",
    NodeKind.CREATOR: "The Creator",
    NodeKind.FOREIGN_GOD: "Foreign god",
    NodeKind.WORLD: "World",
    NodeKind.STAR: "Star",
    NodeKind.GALAXY: "Galaxy",
    NodeKind.CLUSTER: "Cluster",
    NodeKind.DIMENSION: "Dimension",
}
KINDS: tuple[tuple[str, Mapping[Any, Any]], ...] = (
    ("Kinds of worlds", WORLD_TYPES),
    ("Kinds of stars", STAR_TYPES),
    ("Kinds of galaxies", GALAXY_TYPES),
    ("Zones of a galaxy", GALACTIC_ZONES),
    ("Structures of a galaxy", STRUCTURE_KINDS),
    ("Events of a galaxy", GALACTIC_EVENT_LABELS),
    ("Kinds of clusters", CLUSTER_KINDS),
    ("Kinds of dimensions", DIMENSION_KINDS),
    ("Events between dimensions", DIMENSIONAL_EVENT_LABELS),
    ("Phenomena of the heavens", PHENOMENON_KINDS),
    ("Kinds of cosmic beings", BEING_KINDS),
    ("Climate eras", CLIMATES),
    ("Shapes of the end", APOCALYPSE_LABELS),
    ("Lasting afflictions", PACKAGES),
)


def slug(prefix: str, value: str) -> str:
    return f"{prefix}-{re.sub(r'[^a-z0-9_-]+', '-', value.lower()).strip('-')}"


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


def lower(text: str) -> str:
    return text.replace("_", " ").strip().lower()


def count(number: int, one: str, many: str) -> str:
    return f"{number:,} {one if number == 1 else many}"


def listing(items: list[str]) -> str:
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"


def sort_key(term: str) -> str:
    return term.removeprefix("The ").lower()


def described_catalogues() -> list[tuple[str, Mapping[Any, Any]]]:
    found: dict[int, tuple[str, Mapping[Any, Any]]] = {}
    for module in pkgutil.walk_packages(aerona.catalog.__path__, "aerona.catalog."):
        loaded = importlib.import_module(module.name)
        for name, value in vars(loaded).items():
            if not (name.isupper() and isinstance(value, (dict, MappingProxyType)) and value):
                continue
            key, spec = next(iter(value.items()))
            complete = isinstance(key, enum.Enum) and len(value) == len(type(key))
            if complete and hasattr(spec, "label") and hasattr(spec, "description"):
                found.setdefault(id(value), (f"{module.name}.{name}", value))
    return sorted(found.values(), key=lambda item: item[0])


class Booklet:
    def __init__(self) -> None:
        self.rules = Rules()
        data = json.loads(TERMS.read_text(encoding="utf-8"))
        self.app_terms = dict(APP_TERM.findall(GLOSSARY.read_text(encoding="utf-8")))
        self.app_turkish: dict[str, str] = data["app_terms"]
        self.terms: list[dict[str, str]] = data["terms"]
        self.nodes: dict[str, dict[str, str]] = data["nodes"]
        self.types: dict[str, dict[str, str]] = data["entity_types"]
        self.turkish: str = data["turkish_heading"]
        self.check()

    def check(self) -> None:
        problems: list[str] = []
        problems += [f"the in-game word {term} has no Turkish name in app_terms" for term in self.app_terms if term not in self.app_turkish]
        problems += [f"app_terms names {term}, which the in-game glossary does not hold" for term in self.app_turkish if term not in self.app_terms]
        own = [entry["term"] for entry in self.terms]
        problems += [f"the word {term} is in terms and in the in-game glossary; keep it in one" for term in own if term in self.app_terms]
        problems += [f"the word {term} is in terms twice" for term in sorted({term for term in own if own.count(term) > 1})]
        problems += [f"the word {entry.get('term', '?')} needs a term, tr and meaning" for entry in self.terms if set(entry) != {"term", "tr", "meaning"}]
        problems += [f"nodes has no entry for {kind.value}" for kind in NodeKind if kind.value not in self.nodes]
        problems += [f"nodes names {key}, which is no kind of node" for key in self.nodes if key not in {kind.value for kind in NodeKind}]
        problems += [f"entity_types has no entry for {kind.value}" for kind in EntityType if kind.value not in self.types]
        problems += [f"entity_types names {key}, which is no kind of record" for key in self.types if key not in {kind.value for kind in EntityType}]
        problems += [f"the node {kind.value} has no name in NODE_NAMES" for kind in NodeKind if kind not in NODE_NAMES]
        shown = {id(table) for _title, table in KINDS}
        problems += [
            f"the catalogue {name} has labels and descriptions but no section in KINDS" for name, table in described_catalogues() if id(table) not in shown
        ]
        if problems:
            raise SystemExit("The word list is incomplete:\n  " + "\n  ".join(problems))

    def glossary(self) -> list[tuple[str, str, str]]:
        rows = [(term, self.app_turkish[term], meaning) for term, meaning in self.app_terms.items()]
        rows += [(entry["term"], entry["tr"], entry["meaning"]) for entry in self.terms]
        return sorted(rows, key=lambda row: sort_key(row[0]))

    def lines(self) -> list[str]:
        return [
            SIGNATURE,
            "",
            *self.opening(),
            *self.contents(),
            *self.how_to_read(),
            *self.words(),
            *self.node_table(),
            *self.record_table(),
            *self.records(),
            *self.cosmos(),
        ]

    def opening(self) -> list[str]:
        kinds = sum(len(table) for _title, table in KINDS)
        return [
            f"# {APP_NAME}: The Things of the World and Their Names",
            "",
            (
                "Every world is made of things: gods, worlds and stars above, and below them peoples, places, creatures, laws, wars "
                "and every other kind of record. This booklet names each kind, says what it is and what values it holds, "
                "and gives the words of the game with their Turkish names."
            ),
            "",
            "| The world's vocabulary at a glance | |",
            "|---|---:|",
            f"| Words of the game | {len(self.glossary()):,} |",
            f"| Kinds of things with a page of their own | {len(NodeKind):,} |",
            f"| Kinds of records | {len(EntityType):,} |",
            f"| Kinds of records a son can make | {sum(1 for spec in ENTITY_TYPES.values() if spec.creation_tool):,} |",
            f"| Kinds within the world and the cosmos | {kinds:,} in {count(len(KINDS), 'list', 'lists')} |",
            "",
        ]

    def contents(self) -> list[str]:
        return [
            "## Contents",
            "",
            "1. [How to read this booklet](#how-to-read-this-booklet)",
            "2. [Words of the game](#words-of-the-game)",
            "3. [The kinds of things](#the-kinds-of-things)",
            "4. [The kinds of records](#the-kinds-of-records)",
            "5. [Each kind of record](#each-kind-of-record)",
            "6. [Kinds within the world and the cosmos](#kinds-within-the-world-and-the-cosmos)",
            *(f"   - [{title}](#{slug('k', title)}) ({len(table):,})" for title, table in KINDS),
            "",
        ]

    def how_to_read(self) -> list[str]:
        return [
            "## How to read this booklet",
            "",
            "- **Words of the game** explains the words the game and the other booklets use, with the Turkish name of each.",
            "- **The kinds of things** are the things that have a page of their own in the game: you, your sons, foreign gods, worlds, stars and the rest.",
            (
                "- **The kinds of records** are the kinds of things that live in a world. "
                "Each has its values, the places it can live in and the tool a son makes it with."
            ),
            "- Ranges are those of a new world and follow your world's rules.",
            "- Kinds a son cannot make are made by the world itself as it lives, and by you through the powers in *The Powers of a God*.",
            "",
        ]

    def words(self) -> list[str]:
        lines = [
            "## Words of the game",
            "",
            f"| Word | {self.turkish} | What it means |",
            "|---|---|---|",
        ]
        for term, turkish, meaning in self.glossary():
            lines.append(f'| <a id="{slug("w", term)}"></a>**{cell(term)}** | {cell(turkish)} | {cell(meaning)} |')
        return [*lines, ""]

    def node_table(self) -> list[str]:
        lines = [
            "## The kinds of things",
            "",
            "Each of these has a page of its own that opens when you pick it by name.",
            "",
            f"| Kind | {self.turkish} | What it is |",
            "|---|---|---|",
        ]
        for kind in NodeKind:
            entry = self.nodes[kind.value]
            name = NODE_NAMES[kind]
            target = f"[{name}](#each-kind-of-record)" if kind is NodeKind.ENTITY else f"**{name}**"
            lines.append(f"| {target} | {cell(entry['tr'])} | {cell(entry['meaning'])} |")
        return [*lines, ""]

    def record_table(self) -> list[str]:
        lines = [
            "## The kinds of records",
            "",
            f"| Kind | {self.turkish} | Made by | Lives in |",
            "|---|---|---|---|",
        ]
        for kind in EntityType:
            spec = ENTITY_TYPES[kind]
            lines.append(f"| [{spec.label}](#{slug('r', kind.value)}) | {cell(self.types[kind.value]['tr'])} | {self.maker(spec)} | {self.home(spec) or '—'} |")
        return [*lines, ""]

    def maker(self, spec: EntityTypeSpec) -> str:
        if spec.creation_tool is None:
            return "the world"
        return f"sons, with [{lower(spec.creation_tool)}]({TOOLS}#{slug('t', f'son-{spec.creation_tool}')})"

    def home(self, spec: EntityTypeSpec) -> str:
        homes = [ENTITY_TYPES[kind].plural.lower() for kind in EntityType if kind in spec.containers]
        return listing(homes) if homes else ""

    def range_of(self, low: int, high: int | None) -> str:
        return f"{low:,} to {high:,}" if high is not None else f"from {low:,}"

    def records(self) -> list[str]:
        lines = ["## Each kind of record", ""]
        for kind in EntityType:
            spec = ENTITY_TYPES[kind]
            entry = self.types[kind.value]
            lines += [
                f'<a id="{slug("r", kind.value)}"></a>',
                "",
                f"### {spec.label}",
                "",
                f"*{entry['tr']}*. {entry['meaning']}",
                "",
            ]
            facts = [f"**Made by** {self.maker(spec)}."]
            home = self.home(spec)
            if home:
                facts.append(f"**Lives in** {home}" + (", and always stands in one." if spec.location_required else "."))
            else:
                facts.append("**Stands** on its own, in no other record.")
            if spec.engine_kinds:
                facts.append(f"**Subtypes** the world knows: {listing(sorted(lower(item.value) for item in spec.engine_kinds))}.")
            lines += [f"- {fact}" for fact in facts]
            lines.append("")
            if spec.stats:
                lines += ["| Value | Range |", "|---|---|"]
                lines += [f"| {cell(field.label)} | {self.range_of(*field.bounds(self.rules))} |" for field in spec.stats]
                lines.append("")
        return lines

    def cosmos(self) -> list[str]:
        lines = ["## Kinds within the world and the cosmos", ""]
        for title, table in KINDS:
            lines += [
                f'<a id="{slug("k", title)}"></a>',
                "",
                f"### {title}",
                "",
                "| Kind | What it is |",
                "|---|---|",
            ]
            lines += [f"| **{cell(spec.label)}** | {cell(spec.description)} |" for spec in table.values()]
            lines.append("")
        return lines


def broken_links(text: str) -> list[str]:
    anchors = set(ANCHOR.findall(text))
    headings = {re.sub(r"[^a-z0-9 -]", "", line.lstrip("#").strip().lower()).replace(" ", "-") for line in text.splitlines() if line.startswith("## ")}
    return sorted({target for target in LINK.findall(text) if target not in anchors and target not in headings})


def missing_entries(text: str) -> list[str]:
    anchors = set(ANCHOR.findall(text))
    return sorted({slug("r", kind.value) for kind in EntityType} - anchors)


def missing_tools(text: str) -> list[str]:
    companion = ROOT / "docs" / "mechanics" / TOOLS
    if not companion.exists():
        return []
    known = set(ANCHOR.findall(companion.read_text(encoding="utf-8")))
    return sorted({target for target in re.findall(rf"\]\({re.escape(TOOLS)}#([^)]+)\)", text) if target not in known})


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
    parser = argparse.ArgumentParser(description="Write the booklet of every kind of thing in the world and the words of the game, as one Markdown file.")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Markdown file to write (default: {DEFAULT_OUTPUT.relative_to(ROOT)})",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="print the Markdown instead of writing a file",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing file that this script did not write",
    )
    arguments = parser.parse_args()
    text = "\n".join(Booklet().lines()).rstrip() + "\n"
    problems = (
        [f"broken link #{target}" for target in broken_links(text)]
        + [f"missing entry #{target}" for target in missing_entries(text)]
        + [f"no tool {TOOLS}#{target}" for target in missing_tools(text)]
    )
    if problems:
        print(
            "The booklet is incomplete, nothing was written:",
            *problems,
            sep="\n  ",
            file=sys.stderr,
        )
        return 1
    if arguments.stdout:
        sys.stdout.write(text)
        return 0
    output = arguments.out.resolve()
    if not arguments.force and not ours(output):
        print(
            f"{output} exists and was not written by this script; pass --force or choose another --out.",
            file=sys.stderr,
        )
        return 2
    write_atomically(output, text)
    print(f"Wrote {output} ({len(text.encode('utf-8')) / 1_048_576:.2f} MB, {count(len(EntityType), 'kind of record', 'kinds of record')}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
