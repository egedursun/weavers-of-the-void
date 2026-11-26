import argparse
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

from aerona.agents.mortal import SPEAKING_DEAD
from aerona.catalog.civilization import required_tier
from aerona.constants.app import APP_NAME
from aerona.core.grammar import plural
from aerona.domain.enums.agent import AgentKind, PendingJobKind
from aerona.domain.enums.entity import AGENT_TYPES, EntityType
from aerona.domain.enums.rarity import Rarity
from aerona.engine.interconnect.catalog import REGISTERED
from aerona.engine.interconnect.registry import Mechanic, Subsystem
from aerona.prompts import MortalToolId, SonToolId, tool_text
from aerona.prompts.tools.context import ToolTextContext
from aerona.rules.registry import Rules
from aerona.tools.framework.spec import ToolSpec
from aerona.tools.mortal.registry import (
    ACTOR_TYPES,
    SPIRIT_TOOLS,
    TIER_GATES,
    mortal_specs,
)
from aerona.tools.mortal.registry import AGE_LIMITS as MORTAL_LIMITS
from aerona.tools.son.availability import AGE_LIMITS as SON_LIMITS
from aerona.tools.son.registry import son_specs

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "docs" / "mechanics" / "agent-tools.md"
SIGNATURE = f'[booklet]: # "{APP_NAME} booklet: the deeds of sons and mortals"'
CONNECTIONS = "interconnections.md"
ANCHOR = re.compile(r'<a id="([^"]+)"></a>')
LINK = re.compile(r"\]\(#([^)]+)\)")
PART_NAMES = {Subsystem.SOCIAL: "Society"}
CHEVRON = "\u203a"
SEEING = "seeing"
SEEING_NAME = "Seeing the world"
SEEING_ABOUT = (
    "Tools that only look: they show the world, a thing or a memory more fully than the turn's own picture of it. They cost nothing and change nothing."
)
AGENTS: dict[AgentKind, tuple[str, str]] = {
    AgentKind.SON: (
        "The tools of the sons",
        (
            "Your sons are gods. Each epoch every son takes a turn: it reads its world and acts through the tools below, "
            "spending action points and essence. A tool is offered only when it can work in that son's world."
        ),
    ),
    AgentKind.MORTAL: (
        "The tools of the mortals",
        (
            "The notable mortals and the communities of a world act too. Each epoch they take a turn of their own and act through "
            "the tools below. A tool is offered only to those who may use it and only when it can work where they stand."
        ),
    ),
}
LONG_JOBS = {
    PendingJobKind.WORLD_BIRTH: "a new world is born when the turn is over",
    PendingJobKind.CHILD_BIRTH: "a new son is born when the turn is over",
}
TOOL_PARTS: dict[str, Subsystem] = {
    "coin_words": Subsystem.LANGUAGE,
    "reshape_season": Subsystem.ENVIRONMENT,
    "make_will": Subsystem.LAW,
    "found_language": Subsystem.LANGUAGE,
    "rebel": Subsystem.GODS,
    "pray_to_creator": Subsystem.GODS,
    "war_on_foreign_god": Subsystem.GODS,
    "resurrect_sibling": Subsystem.GODS,
    "hinder_return": Subsystem.GODS,
    "challenge_god": Subsystem.GODS,
    "harvest_resource": Subsystem.ECONOMY,
    "open_road": Subsystem.ECONOMY,
    "establish_trade": Subsystem.ECONOMY,
    "barter": Subsystem.ECONOMY,
    "lend": Subsystem.ECONOMY,
    "repay_debt": Subsystem.ECONOMY,
    "open_cosmic_bed": Subsystem.COSMOS,
    "find_route": Subsystem.COSMOS,
    "build_ship": Subsystem.COSMOS,
    "launch_expedition": Subsystem.COSMOS,
    "incite_war": Subsystem.WAR,
    "declare_war": Subsystem.WAR,
    "raise_army": Subsystem.WAR,
    "appoint_commander": Subsystem.WAR,
    "bless_host": Subsystem.WAR,
    "escape": Subsystem.WAR,
    "pay_ransom": Subsystem.WAR,
    "rescue_captive": Subsystem.WAR,
    "make_interworld_treaty": Subsystem.POLITY,
    "seal_treaty": Subsystem.POLITY,
    "void_treaty": Subsystem.POLITY,
    "propose_treaty": Subsystem.POLITY,
    "accept_treaty": Subsystem.POLITY,
    "break_treaty": Subsystem.POLITY,
    "diplomacy": Subsystem.POLITY,
    "raise_throne": Subsystem.POLITY,
    "crown_ruler": Subsystem.POLITY,
    "bless_bloodline": Subsystem.HOUSEHOLD,
    "found_house": Subsystem.HOUSEHOLD,
    "adopt": Subsystem.HOUSEHOLD,
    "take_life": Subsystem.BODY,
    "forge_ley_line": Subsystem.MAGIC,
    "lay_magic_site": Subsystem.MAGIC,
    "add_season": Subsystem.ENVIRONMENT,
    "explore_land": Subsystem.ENVIRONMENT,
    "carry_species": Subsystem.ECOLOGY,
    "seed_life": Subsystem.ECOLOGY,
    "call_up_soul": Subsystem.FAITH,
    "worship": Subsystem.FAITH,
    "preach": Subsystem.FAITH,
    "deny_god": Subsystem.FAITH,
    "prophesy": Subsystem.FAITH,
    "resurrection_rite": Subsystem.FAITH,
    "raise_district": Subsystem.SOCIAL,
    "design_district": Subsystem.SOCIAL,
    "go_on_adventure": Subsystem.SOCIAL,
    "sabotage": Subsystem.INTRIGUE,
    "build_spy_network": Subsystem.INTRIGUE,
    "swear_oath": Subsystem.LAW,
}
RARITY_POINTS: dict[Rarity, Callable[[Rules], int]] = {
    Rarity.COMMON: lambda rules: rules.rarities.common_action_points,
    Rarity.UNCOMMON: lambda rules: rules.rarities.uncommon_action_points,
    Rarity.RARE: lambda rules: rules.rarities.rare_action_points,
    Rarity.EPIC: lambda rules: rules.rarities.epic_action_points,
    Rarity.LEGENDARY: lambda rules: rules.rarities.legendary_action_points,
    Rarity.MYTHIC: lambda rules: rules.rarities.mythic_action_points,
}
Spec = ToolSpec[Any, Any]


def slug(prefix: str, value: str) -> str:
    return f"{prefix}-{re.sub(r'[^a-z0-9_-]+', '-', value.lower()).strip('-')}"


def plain(text: str) -> str:
    words = text.replace("_", " ").replace(".", f" {CHEVRON} ").strip()
    return words[:1].upper() + words[1:]


def lower(text: str) -> str:
    return text.replace("_", " ").strip().lower()


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def count(number: int, one: str, many: str) -> str:
    return f"{number:,} {one if number == 1 else many}"


def listing(items: list[str]) -> str:
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"


def field_label(path: str) -> str:
    return f" {CHEVRON} ".join(plain(re.sub(r"_ids?$", "", segment)) for segment in path.split("."))


def part_name(part: Subsystem | str) -> str:
    if part == SEEING:
        return SEEING_NAME
    return PART_NAMES.get(Subsystem(part), plain(str(part)))


def tool_id(spec: Spec) -> SonToolId | MortalToolId:
    return SonToolId(spec.name) if spec.agent is AgentKind.SON else MortalToolId(spec.name)


def anchor(spec: Spec) -> str:
    return slug("t", f"{spec.agent.value}-{spec.name}")


class Booklet:
    def __init__(self) -> None:
        self.rules = Rules()
        self.specs: dict[AgentKind, list[Spec]] = {
            AgentKind.SON: list(son_specs()),
            AgentKind.MORTAL: list(mortal_specs()),
        }
        self.all = [spec for specs in self.specs.values() for spec in specs]
        self.texts = {(spec.agent, spec.name): tool_text(tool_id(spec), self.rules, ToolTextContext()) for spec in self.all}
        self.mechanics: dict[str, list[Mechanic]] = defaultdict(list)
        for mechanic in sorted(REGISTERED.values(), key=lambda item: item.title):
            for name in mechanic.tools:
                self.mechanics[name].append(mechanic)
        self.parts = self.place_parts()
        self.groups: dict[AgentKind, dict[str, list[Spec]]] = {}
        order = [SEEING, *(part.value for part in Subsystem)]
        for agent, specs in self.specs.items():
            grouped: dict[str, list[Spec]] = defaultdict(list)
            for spec in specs:
                grouped[self.parts[(agent, spec.name)]].append(spec)
            self.groups[agent] = {key: sorted(grouped[key], key=lambda spec: spec.name) for key in order if grouped.get(key)}

    def place_parts(self) -> dict[tuple[AgentKind, str], str]:
        modules: dict[str, Counter[Subsystem]] = defaultdict(Counter)
        for spec in self.all:
            for mechanic in self.mechanics.get(spec.name, ()):
                modules[spec.handler.__module__][mechanic.subsystem] += 1
        placed: dict[tuple[AgentKind, str], str] = {}
        unplaced: list[str] = []
        for spec in self.all:
            tally = Counter(mechanic.subsystem for mechanic in self.mechanics.get(spec.name, ())) or modules.get(spec.handler.__module__, Counter())
            if spec.meta.read_only:
                placed[(spec.agent, spec.name)] = SEEING
            elif tally:
                best = max(tally.values())
                placed[(spec.agent, spec.name)] = next(part.value for part in Subsystem if tally.get(part) == best)
            elif spec.name in TOOL_PARTS:
                placed[(spec.agent, spec.name)] = TOOL_PARTS[spec.name].value
            else:
                unplaced.append(f"{spec.agent.value}.{spec.name}")
        if unplaced:
            raise SystemExit(f"These tools reach no mechanic and have no part in TOOL_PARTS of {Path(__file__).name}: {', '.join(unplaced)}")
        return placed

    def limit(self, spec: Spec) -> int | None:
        found = SON_LIMITS.get(SonToolId(spec.name)) if spec.agent is AgentKind.SON else MORTAL_LIMITS.get(MortalToolId(spec.name))
        return found[1](self.rules) if found is not None else None

    def facts(self, spec: Spec) -> list[str]:
        meta = spec.meta
        facts: list[str] = []
        actions = meta.actions(self.rules)
        essence = meta.essence(self.rules)
        if meta.read_only:
            facts.append("**Costs** nothing: it only looks.")
        elif not actions and not essence and not meta.flexible_actions:
            facts.append("**Costs** nothing.")
        else:
            spent = count(actions, "action point", "action points") if actions else "no action points"
            if meta.flexible_actions:
                spent += ", or more when it does more"
            facts.append(f"**Costs** {spent}" + (f" and {essence:,} essence." if essence else "."))
        limit = self.limit(spec)
        if limit is not None:
            facts.append(f"**At most** {count(limit, 'time', 'times')} an epoch.")
        rarity = meta.minimum_rarity(self.rules)
        if rarity is not None:
            facts.append(f"**Only** a son whose card is {lower(rarity.value)} or rarer may use it.")
        if spec.agent is AgentKind.MORTAL:
            allowed = ACTOR_TYPES.get(MortalToolId(spec.name))
            if allowed is not None:
                facts.append(f"**Used by** {listing([self.kind_name(kind) for kind in EntityType if kind in allowed])}.")
            capability = TIER_GATES.get(MortalToolId(spec.name))
            if capability is not None:
                tier = required_tier(self.rules, capability)
                facts.append(f"**Only** a people that has grown to a {lower(tier.name)} or beyond may use it.")
        if meta.long_job is not None:
            facts.append(f"**Takes time:** {LONG_JOBS[meta.long_job]}.")
        reached = self.mechanics.get(spec.name, [])
        if reached:
            links = [f"[{mechanic.title}]({CONNECTIONS}#{slug('m', mechanic.key)})" for mechanic in reached]
            facts.append(f"**Reaches** {listing(links)}.")
        return facts

    def kind_name(self, kind: EntityType) -> str:
        return plural(lower(kind.value))

    def entry(self, spec: Spec) -> list[str]:
        text = self.texts[(spec.agent, spec.name)]
        lines = [
            f'<a id="{anchor(spec)}"></a>',
            "",
            f"#### {plain(spec.name)}",
            "",
            text.description.strip(),
            "",
        ]
        for fact in self.facts(spec):
            lines.append(f"- {fact}")
        lines.append("")
        if text.fields:
            lines += ["| What it chooses | What it means |", "|---|---|"]
            lines += [f"| {cell(field_label(path))} | {cell(meaning.strip())} |" for path, meaning in text.fields.items()]
            lines.append("")
        return lines

    def lines(self) -> list[str]:
        return [
            SIGNATURE,
            "",
            *self.opening(),
            *self.contents(),
            *self.how_to_read(),
            *self.turns(),
            *self.overview(),
            *self.chapters(),
        ]

    def opening(self) -> list[str]:
        acting = [spec for spec in self.all if not spec.meta.read_only]
        reached = {mechanic.key for spec in self.all for mechanic in self.mechanics.get(spec.name, ())}
        return [
            f"# {APP_NAME}: The Deeds of Sons and Mortals",
            "",
            (
                "The world does not wait for you. Every epoch your sons and the notable mortals of each world take their own turns: "
                "each reads its world, decides what it wants and acts. What they can do is fixed by the tools in this booklet. "
                "Every tool runs through the rules of the world, so a deed always has a cost, a reach and a trace in the record."
            ),
            "",
            "| The deeds at a glance | |",
            "|---|---:|",
            f"| Tools of the sons | {len(self.specs[AgentKind.SON]):,} |",
            f"| Tools of the mortals | {len(self.specs[AgentKind.MORTAL]):,} |",
            f"| Tools that only look | {sum(1 for spec in self.all if spec.meta.read_only):,} |",
            f"| Tools that cost essence | {sum(1 for spec in acting if spec.meta.essence(self.rules)):,} |",
            f"| Tools only rarer sons may use | {sum(1 for spec in self.all if spec.meta.rarity_gate is not None):,} |",
            f"| Tools limited to some times an epoch | {sum(1 for spec in self.all if self.limit(spec) is not None):,} |",
            f"| Tools tied to a mechanic of the world | {sum(1 for spec in self.all if self.mechanics.get(spec.name)):,} |",
            f"| Mechanics the tools reach | {len(reached):,} |",
            "",
        ]

    def contents(self) -> list[str]:
        lines = [
            "## Contents",
            "",
            "1. [How to read this booklet](#how-to-read-this-booklet)",
            "2. [A turn](#a-turn)",
            "3. [The parts of the world](#the-parts-of-the-world)",
        ]
        for position, (agent, (title, _about)) in enumerate(AGENTS.items(), start=4):
            lines.append(f"{position}. [{title}](#{slug('a', agent.value)})")
            lines += [f"   - [{part_name(part)}](#{slug('p', f'{agent.value}-{part}')}) ({len(specs):,})" for part, specs in self.groups[agent].items()]
        return [*lines, ""]

    def how_to_read(self) -> list[str]:
        return [
            "## How to read this booklet",
            "",
            (
                "- Tools are gathered by who uses them, the sons or the mortals, and then by the **part of the world** they act on, "
                "the same parts as in the companion booklet *How the World Connects*."
            ),
            "- Each tool is described in the words the son or mortal reads when it chooses. **You** in those words is the one who uses the tool.",
            "- In the tools' own words an **age** is an epoch.",
            (
                "- Numbers are those of a new world. They follow your world's rules, so they change when you change those rules "
                "(see the companion booklet *The Rules of the World*)."
            ),
            "- **What it chooses** lists what the son or mortal decides when it uses the tool.",
            "- **Reaches** links to the mechanics of the world the tool sets in motion.",
            "- You can see every deed in the chronicle and the ledger, and you can change, hold or undo what it made with the powers in *The Powers of a God*.",
            "",
        ]

    def turns(self) -> list[str]:
        agents = [self.kind_name(kind) for kind in EntityType if kind in AGENT_TYPES or kind in SPEAKING_DEAD]
        spirits = sorted(plain(tool.value) for tool in SPIRIT_TOOLS)
        lines = [
            "## A turn",
            "",
            (
                "Each son and each acting mortal gets one turn an epoch. A turn has a budget of **action points**: "
                f"most tools spend {count(self.rules.son_tools.standard_action_cost, 'point', 'points')}, tools that only look spend none, "
                "and a few spend more. A son also spends its own **essence** on great works."
            ),
            "",
            "A son's action points follow the rarity of its card:",
            "",
            "| Rarity | Action points |",
            "|---|---:|",
            *(f"| {plain(rarity.value)} | {points(self.rules):,} |" for rarity, points in RARITY_POINTS.items()),
            "",
            (
                f"A mortal has {count(self.rules.mortal_agents.action_points, 'action point', 'action points')} a turn. "
                f"Mortal turns are taken by {listing(agents)}. Spirits use only these tools: {listing(spirits)}."
            ),
            "",
        ]
        return lines

    def overview(self) -> list[str]:
        lines = [
            "## The parts of the world",
            "",
            "| Part | Tools of the sons | Tools of the mortals |",
            "|---|---:|---:|",
        ]
        for part in [SEEING, *(item.value for item in Subsystem)]:
            counts = [len(self.groups[agent].get(part, [])) for agent in AGENTS]
            if any(counts):
                cells = [f"[{seen:,}](#{slug('p', f'{agent.value}-{part}')})" if seen else "—" for agent, seen in zip(AGENTS, counts, strict=True)]
                lines.append(f"| {part_name(part)} | {' | '.join(cells)} |")
        return [*lines, ""]

    def chapters(self) -> list[str]:
        lines: list[str] = []
        for agent, (title, about) in AGENTS.items():
            lines += [
                f'<a id="{slug("a", agent.value)}"></a>',
                "",
                f"## {title}",
                "",
                about,
                "",
            ]
            for part, specs in self.groups[agent].items():
                lines += [
                    f'<a id="{slug("p", f"{agent.value}-{part}")}"></a>',
                    "",
                    f"### {part_name(part)}",
                    "",
                ]
                if part == SEEING:
                    lines += [SEEING_ABOUT, ""]
                lines += [
                    f"{count(len(specs), 'tool', 'tools')}: " + ", ".join(f"[{lower(spec.name)}](#{anchor(spec)})" for spec in specs) + ".",
                    "",
                ]
                for spec in specs:
                    lines += self.entry(spec)
        return lines


def broken_links(text: str) -> list[str]:
    anchors = set(ANCHOR.findall(text))
    headings = {re.sub(r"[^a-z0-9 -]", "", line.lstrip("#").strip().lower()).replace(" ", "-") for line in text.splitlines() if line.startswith("## ")}
    return sorted({target for target in LINK.findall(text) if target not in anchors and target not in headings})


def missing_entries(text: str) -> list[str]:
    anchors = set(ANCHOR.findall(text))
    specs: list[Spec] = [*son_specs(), *mortal_specs()]
    return sorted({anchor(spec) for spec in specs} - anchors)


def missing_mechanics(text: str) -> list[str]:
    companion = ROOT / "docs" / "mechanics" / CONNECTIONS
    if not companion.exists():
        return []
    known = set(ANCHOR.findall(companion.read_text(encoding="utf-8")))
    return sorted({target for target in re.findall(rf"\]\({re.escape(CONNECTIONS)}#([^)]+)\)", text) if target not in known})


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
    parser = argparse.ArgumentParser(description="Write the booklet of every tool the sons and mortals act through, as one Markdown file.")
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
        + [f"no mechanic {CONNECTIONS}#{target}" for target in missing_mechanics(text)]
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
    tools = len(son_specs()) + len(mortal_specs())
    print(f"Wrote {output} ({len(text.encode('utf-8')) / 1_048_576:.1f} MB, {count(tools, 'tool', 'tools')}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
