import argparse
import os
import re
import sys
import tempfile
import types
import typing
from collections import Counter, defaultdict
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from aerona.constants.app import APP_NAME
from aerona.core.grammar import singular
from aerona.rules.registry import Rules
from aerona.services.player.catalog import ACTIONS, ActionGroup, ActionMode, ActionSpec
from aerona.services.player.family_rows import FAMILY_TABLES
from annotated_types import Ge, Gt, Le, Lt, MaxLen
from check_control import FIXED_COLUMNS, Code, levers, load_modules
from pydantic import BaseModel
from pydantic.fields import FieldInfo

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend" / "src"
DEFAULT_OUTPUT = ROOT / "docs" / "god-powers.md"
SIGNATURE = f'[booklet]: # "{APP_NAME} booklet: the powers of a god"'
ANCHOR = re.compile(r'<a id="([^"]+)"></a>')
LINK = re.compile(r"\]\(#([^)]+)\)")
IMPORT = re.compile(r"""(?:\bfrom\s+|\bimport\s*\(\s*|\bimport\s+)['"]([^'"]+)['"]""")
ROUTE_ID = re.compile(r"createFileRoute\(\s*'([^']*)'")
NAV_ITEM = re.compile(
    r"\{[^{}]*?\bid:\s*'([^']+)',[^{}]*?\btitle:\s*'([^']+)',[^{}]*?\bto:\s*'([^']+)',[^{}]*?\bdescription:\s*(?:'((?:[^'\\]|\\.)*)'|\"([^\"]*)\")[^{}]*?\}",
    re.DOTALL,
)
DRAWER_PAGE = re.compile(r"""['"]?([\w-]+)['"]?:\s*lazy\(\s*\(\)\s*=>\s*import\(\s*'([^']+)'""")
ALIAS = re.compile(r'Alias\(\s*"[A-Z]+",\s*"([^"]+)",\s*"([^"]+)"')
EXTENSIONS = ("", ".ts", ".tsx", "/index.ts", "/index.tsx")
SHELL_ROUTE = "/_app"
SHELL_NAME = "Always at hand"
SHELL_ABOUT = "The top bar, the side panel, the command palette and the overlays that stay on screen whatever screen is open."
SKIPPED_ROUTES = frozenset({"__root"})
BASELINE_SHARE = 0.1
HIDDEN_COLUMNS = frozenset({"held", "locked"})

GROUPS: dict[ActionGroup, tuple[str, str]] = {
    ActionGroup.CREATOR: (
        "The Creator",
        "You are the Creator. These powers shape who the Creator is, how the Creator feels and how the sons and the peoples see the Creator.",
    ),
    ActionGroup.SONS: (
        "The sons",
        "The sons are the gods you summon. Each acts on its own once an epoch. These powers summon, shape, guide, punish and reward them.",
    ),
    ActionGroup.GOD_POWER: (
        "Divine power",
        "The direct strength of the gods: wielding a power, draining or devouring another being, commanding outright, and the magic mortals hold.",
    ),
    ActionGroup.DEATH: (
        "Death and return",
        "What happens when a god or a mortal dies: killing, shielding, resurrecting, the afterlife a faith teaches and the goods of a grave.",
    ),
    ActionGroup.MESSAGES: (
        "Messages",
        "The ways you speak to your sons and to mortals: a command, a dream, the answer to a prayer.",
    ),
    ActionGroup.INTERVENTIONS: (
        "Interventions",
        "Acts that reach straight into a world: miracles, disasters, teachings, curses, outbreaks and their cures.",
    ),
    ActionGroup.ENTITIES: (
        "Things and beings",
        (
            "Every person, people, place, creature and object in a world is a thing. "
            "These powers move, change, mark and end things, and reach into their bodies and minds."
        ),
    ),
    ActionGroup.DIPLOMACY: (
        "Realms and diplomacy",
        "How realms deal with one another: war and peace, alliances, treaties, betrayals, crises, titles, messages and ciphers.",
    ),
    ActionGroup.CANON: (
        "Canon",
        "What is true in your world: canon facts, story threads, bonds between things, map notes, merged records and the names of epochs.",
    ),
    ActionGroup.COSMOS: (
        "The cosmos",
        (
            "Everything above the worlds: stars, galaxies, routes between worlds, the travel resource, "
            "falling bodies, the weather of space and the laws of nature."
        ),
    ),
    ActionGroup.WORLDS: (
        "Worlds and lands",
        "The worlds themselves and every land on them: regions, places, climate, weather, events and the land that is protected or worked.",
    ),
    ActionGroup.FOREIGN_GODS: (
        "Foreign gods",
        "The gods that were there before your sons: placing them, waking them, letting them act, and the faith the peoples keep in them.",
    ),
    ActionGroup.GOALS: (
        "Goals and scenarios",
        "The aims you play toward: scenarios, goals of your own, and when they are weighed.",
    ),
    ActionGroup.SETTINGS: (
        "World settings",
        "Settings of the whole world and of the engine: pinning a value so no mechanic changes it, holding a modifier, writing a happening into history.",
    ),
    ActionGroup.SOCIETY: (
        "Peoples and societies",
        "The life of mortals together: peoples, settlements, families, classes, work, trade, money, law, faith, learning, the arts and every custom.",
    ),
    ActionGroup.WARFARE: (
        "War",
        "Armies, fleets, vehicles and their parts, equipment, formations, battles, sieges and the fate of captives.",
    ),
    ActionGroup.CREATURES: (
        "Creatures and living things",
        "Kinds of life and their bodies: beasts, plants, crops, how they range, how they change and when they awaken to thought.",
    ),
    ActionGroup.BEYOND: (
        "The Beyond",
        "What lies outside the ordinary world: dimensions, rifts, cosmic beings, souls, sources of power and the doom clock.",
    ),
    ActionGroup.LANGUAGES: (
        "Languages",
        "The tongues of the world: their words, their sounds, who speaks them, the sacred tongues of gods and the policies of realms on speech.",
    ),
    ActionGroup.MEMORY: (
        "Memory and legend",
        "What the world remembers and believes: legends, prophecies, rumours, histories and how far each one trusts a source.",
    ),
    ActionGroup.FATE: (
        "Fate",
        "Fate tells the story of every epoch. These powers set fortune, omens, hidden truths, the beats of a tale and the debt Fate keeps.",
    ),
}

VERBS = {
    "create": "Bring a new one into the world.",
    "edit": "Change any of its values.",
    "delete": "Take it out of the world.",
    "set": "Give it a value outright.",
    "remove": "Take it away from where it is.",
    "release": "Let a held value follow the world again.",
    "hold": "Keep it as it is, so the engine cannot change it.",
    "run": "Make the engine do it now.",
    "found": "Found a new one.",
    "add": "Add one to what is there.",
    "open": "Open it.",
    "grant": "Give it to someone.",
    "end": "Bring it to an end.",
}

THING_PAGE = (
    "A thing's page",
    (
        "The page that opens when you pick anything by name: a person, a people, a place, a creature, an object, a son, a foreign god, a world, "
        "a star, a galaxy, a cluster, a dimension or the Creator. It shows the sections that fit what you picked."
    ),
)
DRAWER_PAGES = {
    "son": ("thing", *THING_PAGE),
    "entity": ("thing", *THING_PAGE),
    "foreign-god": ("thing", *THING_PAGE),
    "world": ("thing", *THING_PAGE),
    "star": ("thing", *THING_PAGE),
    "creator": ("thing", *THING_PAGE),
    "galaxy": ("thing", *THING_PAGE),
    "cluster": ("thing", *THING_PAGE),
    "dimension": ("thing", *THING_PAGE),
    "world-guide": (
        "world-guide",
        "A world's guide",
        "A traveller's guide to one world.",
    ),
    "help": ("help", "Help", "The help pages."),
    "incident": (
        "incident",
        "A happening's page",
        "The page of one happening in history.",
    ),
}
SETTINGS_URL = "/settings"
CHEVRON = "\u203a"
SETTINGS_ID = "settings"
OVERVIEW_URL = "/"
SKIPPED_PLACES = frozenset({"design"})
MAKING_VERBS = frozenset({"create", "found", "add", "make", "set"})
ID_SUFFIXES = ("_entity_ids", "_node_ids", "_entity_id", "_node_id", "_ids", "_id")

FIELD_MEANINGS = {
    "hold": "yes or no: keep the result as it is, so the engine cannot change it",
    "release": "values to let follow the world again",
    "confirm": "the word you type to confirm",
    "key": "which one",
    "column": "which of its values",
}
FIELD_NAMES = {
    "node": "thing",
    "entity": "thing",
    "key": "record",
    "other": "other thing",
    "column": "value to change",
}
SCREEN_FIELDS = frozenset({"table"})
LAST_FIELDS = ("values", "hold", "release")


def slug(prefix: str, value: str) -> str:
    return f"{prefix}-{re.sub(r'[^a-z0-9_-]+', '-', value.lower()).strip('-')}"


def plain(text: str) -> str:
    words = text.replace("_", " ").replace("-", " ").strip()
    return words[:1].upper() + words[1:]


def lower(text: str) -> str:
    return text.replace("_", " ").strip().lower()


def named(field: str) -> str:
    stem = next(
        (field.removesuffix(suffix) for suffix in ID_SUFFIXES if field.endswith(suffix)),
        field,
    )
    stem = stem.removesuffix("_pct") + " %" if stem.endswith("_pct") else stem
    return lower(FIELD_NAMES.get(stem, stem))


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def count(number: int, one: str, many: str) -> str:
    return f"{number:,} {one if number == 1 else many}"


def subject_of(spec: ActionSpec) -> str:
    return spec.id.split(":", 1)[0] if ":" in spec.id else ""


def verb_of(spec: ActionSpec) -> str:
    return spec.id.split(":", 1)[1] if ":" in spec.id else ""


@dataclass(frozen=True)
class Place:
    key: str
    name: str
    about: str
    order: int


class Places:
    def __init__(self) -> None:
        self.files = {
            path: path.read_text(encoding="utf-8")
            for path in sorted(FRONTEND.rglob("*"))
            if path.suffix in {".ts", ".tsx"} and path.is_file() and "generated" not in path.parts and ".test." not in path.name
        }
        self.edges = {path: self.imports(path, text) for path, text in self.files.items()}
        self.roots = self.find_roots()
        self.reach: dict[Path, set[str]] = defaultdict(set)
        root_files = set(self.roots)
        for root, place in self.roots.items():
            seen = {root}
            stack = [root]
            while stack:
                current = stack.pop()
                self.reach[current].add(place.key)
                for target in self.edges.get(current, ()):
                    if target not in seen and target not in root_files:
                        seen.add(target)
                        stack.append(target)
        self.by_key = {place.key: place for place in self.roots.values()}
        backend = "\n".join(path.read_text(encoding="utf-8") for path in sorted((ROOT / "backend" / "src" / "aerona").rglob("*.py")))
        self.aliases = {lever: path for path, lever in ALIAS.findall(backend)}

    def resolve(self, source: Path, spec: str) -> Path | None:
        if spec.startswith("@/"):
            base = FRONTEND / spec[2:]
        elif spec.startswith("."):
            base = source.parent / spec
        else:
            return None
        for extension in EXTENSIONS:
            candidate = Path(os.path.normpath(f"{base}{extension}"))
            if candidate in self.files:
                return candidate
        return None

    def imports(self, path: Path, text: str) -> list[Path]:
        return sorted({found for spec in IMPORT.findall(text) if (found := self.resolve(path, spec)) is not None})

    def find_roots(self) -> dict[Path, Place]:
        navigation = self.files[FRONTEND / "config" / "navigation.ts"]
        nav: dict[str, tuple[str, str, int]] = {}
        for position, (key, title, url, single, double) in enumerate(NAV_ITEM.findall(navigation)):
            entry = (title, (single or double).replace("\\'", "'"), position)
            nav.setdefault(SETTINGS_URL if key == SETTINGS_ID else url, entry)
        roots: dict[Path, Place] = {}
        offset = len(nav)
        for path in sorted((FRONTEND / "routes").rglob("*.tsx")):
            found = ROUTE_ID.search(self.files.get(path, ""))
            if found is None or path.stem in SKIPPED_ROUTES or found.group(1).removeprefix(f"{SHELL_ROUTE}/") in SKIPPED_PLACES:
                continue
            route = found.group(1)
            if route == SHELL_ROUTE:
                roots[path] = Place("shell", SHELL_NAME, SHELL_ABOUT, offset * 2 + len(DRAWER_PAGES) + 1)
                continue
            url = route.removeprefix(SHELL_ROUTE).rstrip("/") or "/"
            title, about, position = nav.get(url, (plain(url.rsplit("/", 1)[-1]), "", offset))
            if url.startswith(f"{SETTINGS_URL}/"):
                title = f"Settings {CHEVRON} {title}"
            later = len(nav) if url.startswith(SETTINGS_URL) else 0
            roots[path] = Place(
                "overview" if url == OVERVIEW_URL else url.strip("/"),
                title,
                about,
                position + later,
            )
        pages = self.files[FRONTEND / "config" / "entryPages.ts"]
        for position, (key, module) in enumerate(DRAWER_PAGE.findall(pages), start=offset * 2 + 1):
            if key not in DRAWER_PAGES:
                raise SystemExit(f"The drawer page {key} has no name in DRAWER_PAGES of {Path(__file__).name}.")
            target = self.resolve(FRONTEND / "config" / "entryPages.ts", module)
            if target is None:
                raise SystemExit(f"The drawer page {key} imports {module}, which does not exist.")
            place, name, about = DRAWER_PAGES[key]
            roots[target] = Place(f"page-{place}", name, about, position)
        return roots

    def calling_files(self, lever: str) -> list[Path]:
        quoted = (f"'{lever}'", f'"{lever}"', f"`{lever}`", f"/actions/{lever}")
        found = [path for path, text in self.files.items() if any(form in text for form in quoted)]
        if lever in self.aliases:
            pattern = re.compile(
                re.sub(
                    r"\\\{[^}]+\\\}",
                    r"[^/'\"`]+",
                    re.escape(f"/api{self.aliases[lever]}"),
                )
                + r"['\"`?]"
            )
            found += [path for path, text in self.files.items() if pattern.search(text) and path not in found]
        return found or [path for path, text in self.files.items() if lever in text]

    def of(self, lever: str) -> list[Place]:
        keys = {key for path in self.calling_files(lever) for key in self.reach.get(path, ())}
        return sorted(
            (self.by_key[key] for key in keys),
            key=lambda place: (place.order, place.name),
        )


class EditedValues:
    def __init__(self) -> None:
        code = Code(load_modules())
        self.code = code
        found = levers(code)
        self.edited: dict[str, set[str]] = {lever: set(code.reach(key).get("edit", ())) for lever, key in found.items()}
        share = Counter(table for tables in self.edited.values() for table in tables)
        self.baseline = {table for table, seen in share.items() if seen > len(self.edited) * BASELINE_SHARE}

    def table_of(self, spec: ActionSpec) -> str | None:
        if subject_of(spec) in FAMILY_TABLES:
            return FAMILY_TABLES[subject_of(spec)]
        tables = self.edited.get(spec.id, set())
        own = sorted(tables - self.baseline)
        if len(own) == 1:
            return own[0]
        stem = singular(subject_of(spec))
        named = sorted(table for table in tables if stem and singular(table) == stem)
        return named[0] if len(named) == 1 else None

    def columns(self, spec: ActionSpec) -> list[str]:
        name = self.table_of(spec)
        table = self.code.tables.get(name) if name else None
        if table is None:
            return []
        hidden = FIXED_COLUMNS | HIDDEN_COLUMNS
        if verb_of(spec) not in MAKING_VERBS:
            hidden |= set(table.primary) | set(table.node_columns)
        return list(dict.fromkeys(named(column) for column in table.columns if column not in hidden))


def bare(annotation: Any) -> tuple[Any, bool]:
    optional = False
    while True:
        origin = typing.get_origin(annotation)
        if origin is typing.Annotated:
            annotation = typing.get_args(annotation)[0]
            continue
        if origin in (typing.Union, types.UnionType):
            options = [option for option in typing.get_args(annotation) if option is not type(None)]
            optional = optional or len(options) < len(typing.get_args(annotation))
            if len(options) == 1:
                annotation = options[0]
                continue
        return annotation, optional


def bounds(metadata: list[Any]) -> str:
    low = next(
        (item.ge if isinstance(item, Ge) else item.gt for item in metadata if isinstance(item, (Ge, Gt))),
        None,
    )
    high = next(
        (item.le if isinstance(item, Le) else item.lt for item in metadata if isinstance(item, (Le, Lt))),
        None,
    )
    if low is not None and high is not None:
        return f"a number from {low:,} to {high:,}"
    if low is not None:
        return f"a number of at least {low:,}"
    if high is not None:
        return f"a number up to {high:,}"
    return "a number"


def scalar(kind: Any, metadata: list[Any], name: str) -> str:
    if typing.get_origin(kind) is typing.Literal:
        return "one of: " + ", ".join(lower(str(option)) for option in typing.get_args(kind))
    if (kind is int and name.endswith("_id")) or name == "key":
        return f"which {named(name)}"
    simple = {bool: "yes or no", str: "your own words"}
    if kind in simple:
        return simple[kind]
    if kind in (int, float):
        return bounds(metadata)
    return "a value for each name you give" if typing.get_origin(kind) is dict else "a value of your choice"


class Booklet:
    def __init__(self) -> None:
        missing = [group for group in ActionGroup if group not in GROUPS]
        if missing:
            raise SystemExit(f"These groups of powers have no title in GROUPS of {Path(__file__).name}: {', '.join(missing)}")
        self.rules = Rules()
        self.places = Places()
        self.values = EditedValues()
        self.enums: dict[str, type[Enum]] = {}
        self.where = {spec.id: self.places.of(spec.id) for spec in ACTIONS}
        self.groups: dict[ActionGroup, dict[str, list[ActionSpec]]] = {group: {} for group in ActionGroup}
        for spec in ACTIONS:
            self.groups[spec.group].setdefault(subject_of(spec), []).append(spec)
        self.rows = {group: self.chapter_rows(group) for group in ActionGroup if self.groups[group]}

    def subject_name(self, subject: str) -> str:
        return plain(subject) if subject else "Single powers"

    def enum_link(self, kind: type[Enum]) -> str:
        self.enums[kind.__name__] = kind
        return f"one of the [{lower(re.sub(r'(?<!^)(?=[A-Z])', ' ', kind.__name__))} choices](#{slug('e', kind.__name__)}) ({len(kind):,})"

    def describe(self, annotation: Any, metadata: list[Any], name: str) -> str:
        kind, _ = bare(annotation)
        origin = typing.get_origin(kind)
        if isinstance(kind, type) and issubclass(kind, Enum):
            return self.enum_link(kind)
        if origin in (list, tuple, set, frozenset):
            return self.describe_list(kind, metadata, name)
        if isinstance(kind, type) and issubclass(kind, BaseModel):
            return "a group of values: " + ", ".join(lower(field) for field in kind.model_fields)
        return scalar(kind, metadata, name)

    def describe_list(self, kind: Any, metadata: list[Any], name: str) -> str:
        if name.endswith("_ids"):
            return f"which {named(name)}s"
        inner = typing.get_args(kind)
        size = next((item.max_length for item in metadata if isinstance(item, MaxLen)), None)
        listed = self.describe(inner[0], [], name) if inner else "entries"
        return f"a list of up to {size:,}, each {listed}" if size else f"a list, each {listed}"

    def field_text(self, spec: ActionSpec, name: str, info: FieldInfo) -> str:
        if name == "values":
            columns = self.values.columns(spec)
            fallback = "the values of the new record" if verb_of(spec) in MAKING_VERBS else "any value of the record"
            meaning = f"any of {', '.join(columns)}" if columns else fallback
        else:
            meaning = FIELD_MEANINGS.get(name) or self.describe(info.annotation, list(info.metadata), name)
        optional = "" if info.is_required() else " (optional)"
        return f"**{plain(named(name))}**: {meaning}{optional}"

    def inputs(self, spec: ActionSpec) -> str:
        fields = {name: info for name, info in spec.input_model.model_fields.items() if name not in SCREEN_FIELDS}
        if not fields:
            return "Nothing: it acts at once."
        ordered = sorted(
            fields,
            key=lambda name: LAST_FIELDS.index(name) + 1 if name in LAST_FIELDS else 0,
        )
        return "<br>".join(self.field_text(spec, name, fields[name]) for name in ordered)

    def place_links(self, lever: str) -> str:
        found = self.where[lever]
        return ", ".join(f"[{place.name}](#{slug('p', place.key)})" for place in found) or "—"

    def power_cell(self, spec: ActionSpec) -> str:
        notes = []
        if spec.mode is ActionMode.JOB:
            notes.append("a longer work: it runs in the background and shows its progress")
        if spec.confirmation is not None:
            notes.append(f"you type {spec.confirmation.value} to confirm it")
        text = f'<a id="{slug("a", spec.id)}"></a>**{cell(spec.title)}**'
        return text + "".join(f"<br>*{note}*" for note in notes)

    def chapter_rows(self, group: ActionGroup) -> list[str]:
        title, intro = GROUPS[group]
        subjects = self.groups[group]
        total = sum(len(specs) for specs in subjects.values())
        lines = [
            f'<a id="{slug("g", group.value)}"></a>',
            "",
            f"### {title}",
            "",
            intro,
            "",
            f"{count(total, 'power', 'powers')} on {count(len(subjects), 'subject', 'subjects')}.",
            "",
        ]
        for subject in sorted(subjects, key=lambda key: (key != "", self.subject_name(key).lower())):
            lines += [
                f"#### {self.subject_name(subject)}",
                "",
                "| Power | What you choose | Cost | Where |",
                "|---|---|---|---|",
            ]
            for spec in subjects[subject]:
                lines.append(f"| {self.power_cell(spec)} | {cell(self.inputs(spec))} | {cell(spec.cost(self.rules))} | {self.place_links(spec.id)} |")
            lines.append("")
        return lines

    def lines(self) -> list[str]:
        chapters = ["## The powers, chapter by chapter", ""]
        for rows in self.rows.values():
            chapters += rows
        return [
            SIGNATURE,
            "",
            *self.opening(),
            *self.contents(),
            *self.how_to_read(),
            *self.deeds(),
            *self.keeping(),
            *self.place_table(),
            *self.overview(),
            *chapters,
            *self.choices(),
        ]

    def opening(self) -> list[str]:
        costly = sum(1 for spec in ACTIONS if spec.cost(self.rules) != "Free")
        placed = sum(1 for spec in ACTIONS if self.where[spec.id])
        subjects = sum(len(subjects) for subjects in self.groups.values())
        return [
            f"# {APP_NAME}: The Powers of a God",
            "",
            (
                "You play the Creator. The engine lives the world on its own, epoch after epoch, and your sons act on their own too. "
                "Nothing it makes is out of your reach: every person, people, place, creature, god, world and star, every value they hold "
                "and every mechanic that moves them can be made, changed, held or unmade by your hand. This booklet lists every one of those powers, "
                "what you choose when you use it, what it costs and where in the game you find it."
            ),
            "",
            "| Your powers at a glance | |",
            "|---|---:|",
            f"| Powers | {len(ACTIONS):,} |",
            f"| Chapters | {sum(1 for group in ActionGroup if self.groups[group]):,} |",
            f"| Subjects | {subjects:,} |",
            f"| Free powers | {len(ACTIONS) - costly:,} |",
            f"| Powers that cost essence | {costly:,} |",
            f"| Powers that let you hold the result | {sum(1 for spec in ACTIONS if 'hold' in spec.input_model.model_fields):,} |",
            f"| Longer works that run in the background | {sum(1 for spec in ACTIONS if spec.mode is ActionMode.JOB):,} |",
            f"| Powers found on a screen of the game | {placed:,} |",
            "",
        ]

    def contents(self) -> list[str]:
        return [
            "## Contents",
            "",
            "1. [How to read this booklet](#how-to-read-this-booklet)",
            "2. [What a god does](#what-a-god-does)",
            "3. [Holding, undoing and the record](#holding-undoing-and-the-record)",
            "4. [Where the powers live](#where-the-powers-live)",
            "5. [The chapters](#the-chapters)",
            "6. [The powers, chapter by chapter](#the-powers-chapter-by-chapter)",
            *(
                f"   - [{GROUPS[group][0]}](#{slug('g', group.value)}) ({sum(len(specs) for specs in self.groups[group].values()):,})"
                for group in ActionGroup
                if self.groups[group]
            ),
            "7. [The lists you choose from](#the-lists-you-choose-from)",
            "",
        ]

    def how_to_read(self) -> list[str]:
        return [
            "## How to read this booklet",
            "",
            "- The powers are gathered into **chapters** by what they touch: the Creator, the sons, peoples, war, the cosmos and more.",
            "- Within a chapter, powers on the same thing share a **subject**: making, changing and unmaking one kind of record sit together.",
            "- **What you choose** lists what you pick or fill in when you use the power. *Optional* means you may leave it out.",
            "- **Cost** is what the power takes from the Creator's essence. Costs follow your world's rules, so they change when you change those rules.",
            "- **Where** names the screens and pages of the game that offer the power. A page opens over any screen when you pick something by name.",
            (
                "- The companion booklets *How the World Connects* and *The Rules of the World* "
                "describe the mechanics these powers reach and the rules they follow."
            ),
            "",
        ]

    def deeds(self) -> list[str]:
        verbs = Counter(verb_of(spec) for spec in ACTIONS)
        lines = [
            "## What a god does",
            "",
            "Most powers are one of a few deeds done to a kind of record.",
            "",
            "| Deed | Powers | What it does |",
            "|---|---:|---|",
        ]
        for verb, meaning in VERBS.items():
            lines.append(f"| {plain(verb)} | {verbs.get(verb, 0):,} | {meaning} |")
        others = sum(seen for verb, seen in verbs.items() if verb not in VERBS)
        named = sorted({verb for verb in verbs if verb and verb not in VERBS})
        lines.append(f"| Other deeds | {others:,} | {count(len(named), 'rarer deed', 'rarer deeds')} and single powers, each named in its own power below. |")
        return [*lines, ""]

    def keeping(self) -> list[str]:
        def counted(prefix: str) -> int:
            return sum(1 for spec in ACTIONS if spec.id.startswith(prefix))

        return [
            "## Holding, undoing and the record",
            "",
            (
                "- **Holding.** "
                f"{count(sum(1 for spec in ACTIONS if 'hold' in spec.input_model.model_fields), 'power lets', 'powers let')} you hold what you set. "
                "A held value or record stays as you left it: no step of the engine and no son may change it until you release it. "
                f"{count(sum(1 for spec in ACTIONS if 'release' in spec.input_model.model_fields), 'power releases', 'powers release')} held values again."
            ),
            "- **Pinning.** Any single value of any record can be pinned, so that no mechanic changes it, and released later.",
            (
                "- **Your ledger.** Every power you use is written into your ledger with what it changed. From the Ledger screen you can undo an entry, "
                "and the world goes back to how it was before it. A page cannot be torn out while an epoch is running."
            ),
            (
                "- **Changes of the engine.** Every value the engine changes is recorded with its cause, "
                f"and {count(counted('state_change:'), 'power sets', 'powers set')} one back as it was."
            ),
            "- **Backups.** The world is saved before every epoch, and a saved world can be brought back from the settings.",
            "",
        ]

    def place_table(self) -> list[str]:
        tally = Counter(place.key for found in self.where.values() for place in found)
        places = sorted(self.places.by_key.values(), key=lambda place: (place.order, place.name))
        lines = [
            "## Where the powers live",
            "",
            "| Screen or page | What it shows | Powers |",
            "|---|---|---:|",
        ]
        for place in (place for place in places if tally.get(place.key)):
            lines.append(f'| <a id="{slug("p", place.key)}"></a>**{cell(place.name)}** | {cell(place.about) or "—"} | {tally.get(place.key, 0):,} |')
        return [*lines, ""]

    def overview(self) -> list[str]:
        lines = [
            "## The chapters",
            "",
            "| Chapter | Subjects | Powers |",
            "|---|---:|---:|",
        ]
        for group in ActionGroup:
            subjects = self.groups[group]
            if subjects:
                lines.append(f"| [{GROUPS[group][0]}](#{slug('g', group.value)}) | {len(subjects):,} | {sum(len(specs) for specs in subjects.values()):,} |")
        return [*lines, ""]

    def choices(self) -> list[str]:
        lines = [
            "## The lists you choose from",
            "",
            "Where a power asks you to pick one of a list, the whole list is here.",
            "",
        ]
        for name in sorted(self.enums):
            kind = self.enums[name]
            title = plain(re.sub(r"(?<!^)(?=[A-Z])", " ", name).lower())
            lines += [
                f'<a id="{slug("e", name)}"></a>',
                "",
                f"#### {title}",
                "",
                f"{count(len(kind), 'choice', 'choices')}: " + ", ".join(lower(str(member.value)) for member in kind) + ".",
                "",
            ]
        return lines


def broken_links(text: str) -> list[str]:
    anchors = set(ANCHOR.findall(text))
    headings = {re.sub(r"[^a-z0-9 -]", "", line.lstrip("#").strip().lower()).replace(" ", "-") for line in text.splitlines() if line.startswith("## ")}
    return sorted({target for target in LINK.findall(text) if target not in anchors and target not in headings})


def missing_entries(text: str) -> list[str]:
    anchors = set(ANCHOR.findall(text))
    return sorted({slug("a", spec.id) for spec in ACTIONS} - anchors)


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
    parser = argparse.ArgumentParser(description="Write the booklet of every power the god holds, as one Markdown file.")
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
    problems = [f"broken link #{target}" for target in broken_links(text)] + [f"missing entry #{anchor}" for anchor in missing_entries(text)]
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
    print(f"Wrote {output} ({len(text.encode('utf-8')) / 1_048_576:.1f} MB, {count(len(ACTIONS), 'power', 'powers')}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
