import argparse
import ast
import os
import re
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from aerona.agents.roles import AgentRole
from aerona.constants.app import APP_NAME
from aerona.prompts.catalog import PROMPTS
from aerona.prompts.ids import PromptId
from aerona.rules.registry import Rules

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "backend" / "src" / "aerona"
DEFAULT_OUTPUT = ROOT / "docs" / "mechanics" / "ai-roles.md"
TOOLS = "agent-tools.md"
SIGNATURE = f'[booklet]: # "{APP_NAME} booklet: the voices of the world"'
ANCHOR = re.compile(r'<a id="([^"]+)"></a>')
LINK = re.compile(r"\]\(#([^)]+)\)")
RULE_PATH = re.compile(r"\brules\.(\w+)\.(\w+)\b")
CALL_KEYWORDS = ("system", "user")
CHEVRON = "\u203a"


class Stage(StrEnum):
    MAKING = "making"
    EPOCH = "epoch"
    ASKED = "asked"


STAGES = {
    Stage.MAKING: (
        "When a world is made",
        "These roles speak when something new comes into being: a whole world at genesis, a new son, a new world in the cosmos, a people waking.",
    ),
    Stage.EPOCH: (
        "In every epoch",
        (
            "These roles speak in the order of an epoch: the sons act, the mortals act, the world engine lives the years, Fate judges, "
            "the chronicler writes and the peoples speak."
        ),
    ),
    Stage.ASKED: (
        "When you ask, or the world needs it",
        (
            "These roles speak when you call on them from a screen of the game, and some of them also when the world itself needs a text: "
            "a deeper account, an epic, a translation or the words for an image."
        ),
    ),
}


@dataclass(frozen=True)
class Role:
    stage: Stage
    about: str
    tools: str | None = None
    prompts: tuple[PromptId, ...] = ()


ROLES: dict[AgentRole, Role] = {
    AgentRole.GENESIS: Role(
        Stage.MAKING,
        "Turns your seed into a world at genesis: the world's name, its cosmology, its tone and way of naming, the Creator, "
        "the first world, its star and regions, and the first sons.",
    ),
    AgentRole.CREATOR_PORTRAIT: Role(
        Stage.MAKING,
        "Writes the Creator's portrait: title, appearance and temperament.",
    ),
    AgentRole.SUMMONING: Role(
        Stage.MAKING,
        "Writes a new son when you summon one or when a son bears a child: name, title, domains, appearance, temperament and inner life.",
    ),
    AgentRole.SON_POWERS: Role(
        Stage.MAKING,
        "Gives a new son the powers and the way of existing that follow from its domains and nature.",
    ),
    AgentRole.AWAKENING: Role(Stage.MAKING, "Writes the peoples of a world as they wake to awareness."),
    AgentRole.WORLD_BIRTH: Role(
        Stage.MAKING,
        "Writes a new world when a son gives birth to one: where it lies, its type, name, language, cosmology and its physical nature.",
    ),
    AgentRole.SON_TURN: Role(
        Stage.EPOCH,
        "Plays one son's turn. The son reads its world and its memory, decides what it wants and acts through its tools until its action points run out.",
        "a-son",
        (PromptId.SON_TURN_SYSTEM, PromptId.SON_TURN_USER, PromptId.SON_TURN_CONTINUATION),
    ),
    AgentRole.MORTAL_TURN: Role(
        Stage.EPOCH,
        (
            "Plays the turn of a notable mortal or community, including the fallen who still act. "
            "It reads what it can see from where it stands and acts through its tools."
        ),
        "a-mortal",
        (PromptId.MORTAL_TURN_SYSTEM, PromptId.MORTAL_TURN_USER, PromptId.MORTAL_TURN_CONTINUATION, PromptId.FALLEN_SON_TURN),
    ),
    AgentRole.FATE: Role(
        Stage.EPOCH,
        "Judges the epoch once the turns and the world engine are done. Fate decides which new records stay as canon and which are rejected, "
        "names what needs a name, fulfils prophecies, opens, moves and closes the open stories of the world, and rewards the sons.",
    ),
    AgentRole.FATE_EXTRA: Role(
        Stage.EPOCH,
        "Judges the records that did not fit into Fate's main judgment, so none waits unjudged.",
    ),
    AgentRole.NAMING: Role(
        Stage.EPOCH,
        "Names the records that came into being without a name, in the world's own way of naming.",
    ),
    AgentRole.CHRONICLER: Role(
        Stage.EPOCH,
        "Writes the history of the epoch after Fate has judged: the name of the age, its narrative, a one-sentence summary and a section for every world.",
    ),
    AgentRole.CHRONICLE_FIX: Role(
        Stage.EPOCH,
        "Completes the chronicle: writes the section of a world the chronicler left out, and rewrites a passage the chronicle audit found wanting.",
    ),
    AgentRole.VOICES: Role(
        Stage.EPOCH,
        "Writes the voices of the peoples after each epoch: how they see what happened and what they came to believe.",
    ),
    AgentRole.COUNCIL: Role(
        Stage.EPOCH,
        "Holds a council of the gods: the speeches, the motion, the votes and alliances, the decision and its minutes. "
        "A council can meet in an epoch on its own or when you call one.",
    ),
    AgentRole.BOND_SUGGESTION: Role(
        Stage.EPOCH,
        "Suggests bonds for records that stand alone, so that every record is tied into the world.",
    ),
    AgentRole.BOND_NAMING: Role(Stage.EPOCH, "Decides what to call a bond between related records."),
    AgentRole.LOCALISATION: Role(Stage.EPOCH, "Writes the lines of the epoch in the world's lore language."),
    AgentRole.LOST_CHRONICLE: Role(Stage.ASKED, "Writes the chronicle of an epoch whose history was never written."),
    AgentRole.REVELATION: Role(
        Stage.ASKED,
        "Writes a single record you create with your own hand, and records the world itself brings forth through some of its mechanics.",
    ),
    AgentRole.DEEPENING: Role(
        Stage.ASKED,
        "Deepens a record, a star or a world: its history, rumours, sayings, details and hidden truth. "
        "Some records are also deepened on their own at the end of every epoch.",
    ),
    AgentRole.CREATOR_DEPTH: Role(
        Stage.ASKED,
        "Deepens the Creator: history, names, secrets, fears, prohibitions, gifts, desire and sayings.",
    ),
    AgentRole.FOREIGN_GOD_DEPTH: Role(
        Stage.ASKED,
        "Deepens a foreign god: personality, existence, powers, history, worship and its view of your pantheon.",
    ),
    AgentRole.CREATOR_EPIC: Role(Stage.ASKED, "Writes the epic of the Creator."),
    AgentRole.SON_EPIC: Role(
        Stage.ASKED,
        "Writes a son's epic. Old epics are also written anew from time to time as the son's story moves on.",
    ),
    AgentRole.ENTITY_IMAGE_PROMPTS: Role(
        Stage.ASKED,
        "Writes the words an image of a record is drawn from, for the records that have none.",
    ),
    AgentRole.COSMOS_IMAGE_PROMPTS: Role(
        Stage.ASKED,
        "Writes the words an image of a star, a world, a galaxy or another body of the cosmos is drawn from, for those that have none.",
    ),
    AgentRole.TRANSLATION: Role(
        Stage.ASKED,
        "Translates a text into one of the world's own languages, with its pronunciation and word-by-word meaning, "
        "and coins the new words it needs. The world also calls on it when it names things in its own tongues.",
    ),
}


def slug(prefix: str, value: str) -> str:
    return f"{prefix}-{re.sub(r'[^a-z0-9_-]+', '-', value.lower()).strip('-')}"


def lower(text: str) -> str:
    return text.replace("_", " ").strip().lower()


def plain(text: str) -> str:
    words = lower(text)
    return words[:1].upper() + words[1:]


def count(number: int, one: str, many: str) -> str:
    return f"{number:,} {one if number == 1 else many}"


def listing(items: list[str]) -> str:
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"


def module_of(path: Path) -> str:
    return ".".join(path.relative_to(PACKAGE.parent).with_suffix("").parts)


@dataclass
class Site:
    prompts: set[PromptId] = field(default_factory=set)
    outputs: set[str] = field(default_factory=set)
    limits: set[tuple[str, str]] = field(default_factory=set)
    functions: set[str] = field(default_factory=set)


def find_sites() -> dict[AgentRole, Site]:
    by_name = {member.name: member for member in AgentRole}
    sites: dict[AgentRole, Site] = defaultdict(Site)
    for path in sorted(PACKAGE.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for function in ast.walk(tree):
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for call in ast.walk(function):
                if not isinstance(call, ast.Call):
                    continue
                keywords = {keyword.arg: keyword.value for keyword in call.keywords if keyword.arg}
                label = keywords.get("label")
                found = re.search(r"AgentRole\.(\w+)", ast.unparse(label)) if label is not None else None
                if found is None or found.group(1) not in by_name:
                    continue
                site = sites[by_name[found.group(1)]]
                site.functions.add(f"{module_of(path)}.{function.name}")
                for key in CALL_KEYWORDS:
                    if key in keywords:
                        site.prompts.update(PromptId[name] for name in re.findall(r"PromptId\.(\w+)", ast.unparse(keywords[key])))
                if "output" in keywords:
                    site.outputs.add(ast.unparse(keywords["output"]))
                if "time_limit" in keywords:
                    site.limits.update(RULE_PATH.findall(ast.unparse(keywords["time_limit"])))
    return sites


class Booklet:
    def __init__(self) -> None:
        missing = [role.name for role in AgentRole if role not in ROLES]
        if missing:
            raise SystemExit(f"These roles have no entry in ROLES of {Path(__file__).name}: {', '.join(missing)}")
        self.rules = Rules()
        self.sites = find_sites()
        silent = [role.name for role in AgentRole if role not in self.sites]
        if silent:
            raise SystemExit(f"These roles are never called with a label in the code: {', '.join(silent)}")
        for role, site in self.sites.items():
            site.prompts.update(ROLES[role].prompts)
            site.prompts.update(prompt for prompt, spec in PROMPTS.items() if spec.output is not None and spec.output.__name__ in site.outputs)

    def seconds(self, namespace: str, key: str) -> int:
        value: int = getattr(getattr(self.rules, namespace), key)
        return value

    def writes(self, site: Site) -> list[str]:
        seen: dict[str, None] = {}
        for prompt in sorted(site.prompts, key=lambda item: item.value):
            output = PROMPTS[prompt].output
            if output is not None:
                for name in output.model_fields:
                    seen.setdefault(lower(name), None)
        return list(seen)

    def entry(self, role: AgentRole) -> list[str]:
        spec = ROLES[role]
        site = self.sites[role]
        lines = [
            f'<a id="{slug("v", role.name)}"></a>',
            "",
            f"### {role.value}",
            "",
            spec.about,
            "",
        ]
        facts: list[str] = []
        if spec.tools is not None:
            facts.append(f"**Acts through** the tools listed in [The Deeds of Sons and Mortals]({TOOLS}#{spec.tools}).")
        writes = self.writes(site)
        if writes:
            facts.append(f"**Writes** {listing(writes)}.")
        if site.limits:
            limits = sorted({self.seconds(*path) for path in site.limits})
            facts.append(f"**Time allowed:** {listing([f'{value:,} seconds' for value in limits])}, set by the world rules.")
        if site.prompts:
            names = sorted(f"`{prompt.value}`" for prompt in site.prompts)
            facts.append(f"**Prompts** it is given, in Settings {CHEVRON} Prompts: {listing(names)}.")
        lines += [f"- {fact}" for fact in facts]
        return [*lines, ""]

    def lines(self) -> list[str]:
        return [
            SIGNATURE,
            "",
            *self.opening(),
            *self.contents(),
            *self.how_to_read(),
            *self.overview(),
            *self.chapters(),
        ]

    def opening(self) -> list[str]:
        prompts = {prompt for site in self.sites.values() for prompt in site.prompts}
        return [
            f"# {APP_NAME}: The Voices of the World",
            "",
            (
                "The world engine lives the world by its rules. Language models give it a voice: they play your sons and the notable mortals, "
                "judge each epoch as Fate, write the chronicle and give words to everything the world makes. "
                "This booklet names every one of those roles, when it speaks, what it reads and what it writes."
            ),
            "",
            "| The voices at a glance | |",
            "|---|---:|",
            f"| Roles | {len(AgentRole):,} |",
            *(
                f"| Roles {STAGES[stage][0][0].lower()}{STAGES[stage][0][1:]} | {sum(1 for spec in ROLES.values() if spec.stage is stage):,} |"
                for stage in Stage
            ),
            f"| Prompts the roles are given | {len(prompts):,} |",
            "",
        ]

    def contents(self) -> list[str]:
        lines = [
            "## Contents",
            "",
            "1. [How to read this booklet](#how-to-read-this-booklet)",
            "2. [The roles at a glance](#the-roles-at-a-glance)",
        ]
        for position, stage in enumerate(Stage, start=3):
            lines.append(f"{position}. [{STAGES[stage][0]}](#{slug('s', stage.value)})")
        return [*lines, ""]

    def how_to_read(self) -> list[str]:
        model = self.rules.model
        return [
            "## How to read this booklet",
            "",
            "- The roles are gathered by **when they speak**: when a world is made, in every epoch, or when you ask.",
            (
                "- **Writes** lists what the role must give back. What it is shown first is laid out in its prompts. "
                "What a role writes is checked against the rules of the world before it enters the world; the engine decides what a deed does."
            ),
            (
                "- The roles follow the world's own seed and canon. The game's own text gives them no images, themes, tone or conflict of its own, "
                "so a world becomes whatever kind of lore its seed asks for."
            ),
            (
                f"- Every prompt a role is given can be read in Settings {CHEVRON} Prompts, and every call to a model, with its cost in tokens, "
                "is listed on the Usage screen."
            ),
            (
                "- Each role runs on the models chosen for it under Providers, in order: when one cannot answer, the next is asked. "
                f"A call that fails is tried "
                f"{count(model.retry_attempts, 'time', 'times')} in all, and a turn that breaks off may continue "
                f"{count(model.max_continuations, 'more time', 'more times')}. These are world rules too."
            ),
            "- The companion booklet *The Deeds of Sons and Mortals* lists the tools the turns act through.",
            "",
        ]

    def overview(self) -> list[str]:
        lines = [
            "## The roles at a glance",
            "",
            "| Role | When it speaks |",
            "|---|---|",
        ]
        for stage in Stage:
            for role in AgentRole:
                if ROLES[role].stage is stage:
                    lines.append(f"| [{role.value}](#{slug('v', role.name)}) | {STAGES[stage][0]} |")
        return [*lines, ""]

    def chapters(self) -> list[str]:
        lines: list[str] = []
        for stage in Stage:
            title, about = STAGES[stage]
            lines += [
                f'<a id="{slug("s", stage.value)}"></a>',
                "",
                f"## {title}",
                "",
                about,
                "",
            ]
            for role in AgentRole:
                if ROLES[role].stage is stage:
                    lines += self.entry(role)
        return lines


def broken_links(text: str) -> list[str]:
    anchors = set(ANCHOR.findall(text))
    headings = {re.sub(r"[^a-z0-9 -]", "", line.lstrip("#").strip().lower()).replace(" ", "-") for line in text.splitlines() if line.startswith("## ")}
    return sorted({target for target in LINK.findall(text) if target not in anchors and target not in headings})


def missing_entries(text: str) -> list[str]:
    anchors = set(ANCHOR.findall(text))
    return sorted({slug("v", role.name) for role in AgentRole} - anchors)


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
    parser = argparse.ArgumentParser(description="Write the booklet of every role the language models play, as one Markdown file.")
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
        + [f"no section {TOOLS}#{target}" for target in missing_tools(text)]
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
    print(f"Wrote {output} ({len(text.encode('utf-8')) / 1024:.0f} KB, {count(len(AgentRole), 'role', 'roles')}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
