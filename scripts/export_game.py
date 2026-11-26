import argparse
import os
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

from aerona.catalog.achievements import ACHIEVEMENTS
from aerona.catalog.creator import ACTION_PASSIONS, ACTION_POLARITY, CREATOR_PASSIONS
from aerona.catalog.goal_metrics import CATEGORY_LABELS, METRICS, SCORE_PART_LABELS
from aerona.catalog.powers import POWERS, power_description, power_unlock_levels
from aerona.catalog.rarities import DEFAULT_FIRST_SONS, build_rarity_table
from aerona.catalog.scenarios import SCENARIOS
from aerona.constants.app import APP_NAME
from aerona.domain.enums.action import ActionPolarity
from aerona.domain.enums.limits import MAX_STARS
from aerona.domain.enums.meta import GoalCategory, ScenarioKey, ScoreComponent
from aerona.domain.enums.son import ReputationLabel
from aerona.engine.gods.progress import star_requirement, xp_for_next_level
from aerona.engine.gods.reputation import label_drift
from aerona.rules.model import RuleDescriptor
from aerona.rules.registry import Rules
from aerona.rules.snapshot import catalog

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "docs" / "mechanics" / "game-progress.md"
GLOSSARY = ROOT / "frontend" / "src" / "features" / "help" / "glossary.ts"
TERMS = "world-terms.md"
SIGNATURE = f'[booklet]: # "{APP_NAME} booklet: goals, growth and score"'
ANCHOR = re.compile(r'<a id="([^"]+)"></a>')
LINK = re.compile(r"\]\(#([^)]+)\)")
APP_TERM = re.compile(r"term:\s*'([^']*)',\s*meaning:\s*'([^']*)'", re.DOTALL)
SCORE_PREFIX = "Score:"
SCENARIO_PREFIX = "Scenario points:"
MOOD_PREFIX = "label_"
TIERS = (1, 2, 3)
LEVELS_SHOWN = 10
CUSTOM = ScenarioKey.CUSTOM
DOOM_TERM = "Doom clock"
ESSENCE_TERM = "Divine essence"
MOOD_TERM = "Mood"
ESSENCE_RULES = (
    "balance.creator_starting_essence",
    "balance.creator_essence_regen",
    "balance.creator_essence_soft_cap",
    "essence.over_cap_income_pct",
    "essence.overflow_pct",
    "creator.cult_faith_per_essence",
    "costs.summon_son",
)
DOOM_RULES = ("balance.apocalypse_threshold", "essence.godless_gnaw", "goals.keep_apocalypse_away_pct", "goals.score_apocalypse_penalty")
GROWTH_RULES = (
    "core_rules.xp_per_level",
    "son_tools.level_up_stat_1",
    "son_tools.level_up_stat_2",
    "god_actions.star_stat_gain",
    "core_rules.max_star_extra_action",
)
ASCENSION_RULES = ("ascension.level", "ascension.renown", "ascension.essence_cost")
REPUTATION_MEANINGS = {
    ReputationLabel.LOVED: "The son loves you, without much fear.",
    ReputationLabel.RESPECTED: "The son both loves and fears you.",
    ReputationLabel.FEARED: "The son fears you, without much love.",
    ReputationLabel.HATED: "The son fears you, has little love left and little loyalty.",
    ReputationLabel.FORGOTTEN: "You have long been silent toward the son, and it neither loves nor fears you.",
    ReputationLabel.DISTANT: "You have been silent toward the son for a long time.",
    ReputationLabel.ACKNOWLEDGED: "None of the above: the son knows you, and that is all.",
}


def slug(prefix: str, value: str) -> str:
    return f"{prefix}-{re.sub(r'[^a-z0-9_-]+', '-', value.lower()).strip('-')}"


def lower(text: str) -> str:
    return text.replace("_", " ").strip().lower()


def plain(text: str) -> str:
    words = lower(text)
    return words[:1].upper() + words[1:]


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


def count(number: int, one: str, many: str) -> str:
    return f"{number:,} {one if number == 1 else many}"


def listing(items: list[str]) -> str:
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"


def opening_capital(text: str) -> str:
    words = text.strip()
    return words[:1].upper() + words[1:]


def amount(value: float) -> str:
    return f"{value:,}" if isinstance(value, int) else f"{value:,.6g}"


class Booklet:
    def __init__(self) -> None:
        self.rules = Rules()
        self.descriptors: dict[str, RuleDescriptor] = {descriptor.path: descriptor for descriptor in catalog(self.rules)}
        self.glossary = dict(APP_TERM.findall(GLOSSARY.read_text(encoding="utf-8")))
        problems = [f"the score part {part.value} has no label in SCORE_PART_LABELS" for part in ScoreComponent if part not in SCORE_PART_LABELS]
        problems += [f"the reputation {label.value} has no meaning in REPUTATION_MEANINGS" for label in ReputationLabel if label not in REPUTATION_MEANINGS]
        problems += [f"the goal area {area.value} has no label in CATEGORY_LABELS" for area in GoalCategory if area not in CATEGORY_LABELS]
        named = (*ESSENCE_RULES, *DOOM_RULES, *GROWTH_RULES, *ASCENSION_RULES)
        problems += [f"the rule {path} does not exist" for path in named if path not in self.descriptors]
        problems += [f"the in-game glossary has no word {term}" for term in (DOOM_TERM, ESSENCE_TERM, MOOD_TERM) if term not in self.glossary]
        if problems:
            raise SystemExit("The booklet cannot be written:\n  " + "\n  ".join(problems))

    def rule_rows(self, paths: tuple[str, ...] | list[str]) -> list[str]:
        rows = ["| Rule | In a new world |", "|---|---:|"]
        rows += [f"| {cell(self.descriptors[path].label)} | {amount(self.descriptors[path].default)} |" for path in paths]
        return [*rows, ""]

    def value(self, path: str) -> int:
        return int(self.descriptors[path].default)

    def lines(self) -> list[str]:
        return [
            SIGNATURE,
            "",
            *self.opening(),
            *self.contents(),
            *self.how_to_read(),
            *self.score(),
            *self.goals(),
            *self.achievements(),
            *self.growth(),
            *self.reputation(),
            *self.creator(),
            *self.doom(),
        ]

    def opening(self) -> list[str]:
        tiers = sum(len(TIERS) for _spec in ACHIEVEMENTS.values())
        return [
            f"# {APP_NAME}: Goals, Growth and Score",
            "",
            "A world needs no winner to be worth living, but the game keeps count. Your cosmos earns a score, you can play toward goals "
            "and earn achievements, your sons grow in level, stars and rarity, and the Creator's own essence, mood and the doom clock "
            "rise and fall with what happens. This booklet sets out every part of that game and the numbers behind it.",
            "",
            "| The game at a glance | |",
            "|---|---:|",
            f"| Parts of the score | {len(ScoreComponent):,} |",
            f"| Goals you can play toward | {sum(1 for key in SCENARIOS if key is not CUSTOM):,}, and goals of your own on {len(METRICS):,} measures |",
            f"| Achievements | {len(ACHIEVEMENTS):,}, in {tiers:,} tiers |",
            f"| Rarities of a son | {len(build_rarity_table(self.rules)):,} |",
            f"| Stars a son can wear | {MAX_STARS:,} |",
            f"| Powers a son can awaken | {len(POWERS):,} |",
            "",
        ]

    def contents(self) -> list[str]:
        sections = (
            "Your score",
            "Goals",
            "Achievements",
            "How your sons grow",
            "How your sons see you",
            "The Creator",
            "The doom clock",
        )
        lines = ["## Contents", "", "1. [How to read this booklet](#how-to-read-this-booklet)"]
        lines += [f"{position}. [{title}](#{slug('', title).lstrip('-')})" for position, title in enumerate(sections, start=2)]
        return [*lines, ""]

    def how_to_read(self) -> list[str]:
        return [
            "## How to read this booklet",
            "",
            "- Every number here is that of a new world. Each is a world rule, so it changes when you change the rules in Settings.",
            "- The Goals screen shows your score, your goals and your achievements as they stand. Your sons' pages show their level, stars and rarity.",
            "- The companion booklet *The Powers of a God* lists the powers that start goals, raise stars, lift a son to a higher rarity "
            "and set the doom clock by hand.",
            "",
        ]

    def score(self) -> list[str]:
        rules = [path for path, descriptor in self.descriptors.items() if descriptor.namespace == "goals" and descriptor.label.startswith(SCORE_PREFIX)]
        lines = [
            "## Your score",
            "",
            "Your score is counted again at the end of every epoch. It adds up these parts:",
            "",
            listing([SCORE_PART_LABELS[part] for part in ScoreComponent]) + ".",
            "",
            "Most parts count the things your cosmos holds, each up to a cap. The doom clock takes points away as it nears its threshold. "
            "Achievements and finished goals add the points they are worth.",
            "",
            "| How the score counts | In a new world |",
            "|---|---:|",
        ]
        lines += [f"| {cell(opening_capital(self.descriptors[path].label.removeprefix(SCORE_PREFIX)))} | {amount(self.value(path))} |" for path in rules]
        return [*lines, ""]

    def goals(self) -> list[str]:
        lines = [
            "## Goals",
            "",
            "A goal is a target you choose to play toward. Each finished goal adds its points to your score, and the same goal can then be taken "
            "again at a harder tier. You can also set a goal of your own on any measure below, hold a goal, edit it or let it go.",
            "",
            "| Goal | Area | What it asks | Points | Each harder tier |",
            "|---|---|---|---:|---:|",
        ]
        for key, spec in SCENARIOS.items():
            if key is CUSTOM:
                continue
            target = spec.default_target(self.rules)
            lines.append(
                f'| <a id="{slug("g", key.value)}"></a>**{cell(spec.name(target))}** | {CATEGORY_LABELS[spec.category]} '
                f"| {cell(spec.description(self.rules, target))} | {spec.points(self.rules):,} | +{spec.step(self.rules):,} |"
            )
        lines += ["", "### Measures for goals of your own", "", "| Measure | Area | Better when |", "|---|---|---|"]
        for measure in METRICS.values():
            lines.append(f"| {cell(measure.label)} | {CATEGORY_LABELS[measure.category]} | {'lower' if measure.lower_is_better else 'higher'} |")
        return [*lines, ""]

    def achievements(self) -> list[str]:
        grouped: dict[GoalCategory, list[str]] = defaultdict(list)
        for key, spec in ACHIEVEMENTS.items():
            tiers = [f"{cell(spec.description(self.rules, tier))} ({spec.points(self.rules, tier):,} points)" for tier in TIERS]
            grouped[spec.category].append(f'| <a id="{slug("h", key.value)}"></a>**{cell(spec.title)}** | {" | ".join(tiers)} |')
        lines = [
            "## Achievements",
            "",
            "An achievement is earned on its own when the world reaches it, in three tiers. Each tier adds its points to your score.",
            "",
        ]
        for area in GoalCategory:
            if grouped.get(area):
                lines += [f"### {CATEGORY_LABELS[area]}", "", "| Achievement | Tier I | Tier II | Tier III |", "|---|---|---|---|", *grouped[area], ""]
        return lines

    def growth(self) -> list[str]:
        table = build_rarity_table(self.rules)
        unlocks = power_unlock_levels(self.rules)
        lines = [
            "## How your sons grow",
            "",
            "### Rarity",
            "",
            "Every son is a card of a rarity. The rarity sets its action points, how much essence it regains each epoch, the range of its values, "
            f"the greatest power it may give its creations and how often it is drawn when you summon. A new world starts with "
            f"{listing([table[rarity].label for rarity in DEFAULT_FIRST_SONS])} sons.",
            "",
            "| Rarity | Action points | Essence each epoch | Values from | Values to | Power cap | Steps in a turn | Summon weight |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for profile in table.values():
            weight = f"{profile.summon_weight:,}" if profile.summonable else "never summoned"
            lines.append(
                f"| {profile.label} | {profile.action_points:,} | {profile.essence_regen:,} | {profile.stat_min:,} | {profile.stat_max:,} "
                f"| {profile.power_cap:,} | {profile.max_turns:,} | {weight} |"
            )
        lines += [
            "",
            "### Level",
            "",
            "A son gains experience and fame from its deeds and from reaching its aims. Each level asks for more experience than the last; "
            f"at each level two of its values rise. Its powers awaken at levels {listing([f'{level:,}' for level in unlocks])}.",
            "",
            "| From level | Experience to the next |",
            "|---:|---:|",
            *(f"| {level:,} | {xp_for_next_level(self.rules, level):,} |" for level in range(1, LEVELS_SHOWN + 1)),
            "",
            *self.rule_rows(GROWTH_RULES),
            "### Stars",
            "",
            f"You can give a son a star once it has the level and fame the star asks for; the essence comes from you. "
            f"A son wears up to {count(MAX_STARS, 'star', 'stars')}, every star raises each of its values, and the highest star gives it an extra action.",
            "",
            "| Star | Level needed | Fame needed | Your essence |",
            "|---:|---:|---:|---:|",
        ]
        for target in range(2, MAX_STARS + 1):
            requirement = star_requirement(self.rules, target)
            lines.append(f"| {target:,} | {requirement.level:,} | {requirement.fame:,} | {requirement.essence:,} |")
        lines += [
            "",
            "### Ascension",
            "",
            f"A son that wears all {MAX_STARS:,} stars and has the level and fame below can be lifted to the next rarity. "
            "It starts again at one star, with the values of its new rarity.",
            "",
            *self.rule_rows(ASCENSION_RULES),
            "### Powers",
            "",
            "Each son holds up to three powers, which awaken as it levels.",
            "",
            "| Power | What it does |",
            "|---|---|",
            *(f"| **{cell(spec.name)}** | {cell(power_description(self.rules, effect))} |" for effect, spec in POWERS.items()),
            "",
        ]
        return lines

    def reputation(self) -> list[str]:
        polarity: dict[ActionPolarity, list[str]] = defaultdict(list)
        for kind, side in ACTION_POLARITY.items():
            polarity[side].append(lower(kind.value))
        lines = [
            "## How your sons see you",
            "",
            "Each son holds a view of you, made of love, fear and how long you have been silent toward it. "
            "Kind deeds raise its love, stern deeds its fear. The view decides how its loyalty and wrath drift each epoch.",
            "",
            "| View | When | Loyalty each epoch | Wrath each epoch |",
            "|---|---|---:|---:|",
        ]
        for label in ReputationLabel:
            loyalty, wrath = label_drift(self.rules, label)
            lines.append(f"| {plain(label.value)} | {REPUTATION_MEANINGS[label]} | {loyalty:+,} | {wrath:+,} |")
        lines += [
            "",
            f"- **Kind deeds:** {listing(sorted(polarity[ActionPolarity.BENEVOLENT]))}.",
            f"- **Stern deeds:** {listing(sorted(polarity[ActionPolarity.STERN]))}.",
            "",
        ]
        return lines

    def creator(self) -> list[str]:
        moods = [path for path, descriptor in self.descriptors.items() if descriptor.namespace == "creator" and descriptor.key.startswith(MOOD_PREFIX)]
        feeds: dict[str, list[str]] = defaultdict(list)
        for kind, passions in ACTION_PASSIONS.items():
            for passion in passions:
                feeds[passion.value].append(lower(kind.value))
        lines = [
            "## The Creator",
            "",
            "### Essence",
            "",
            f"{self.glossary[ESSENCE_TERM]} Your powers that cost essence are listed in *The Powers of a God*.",
            "",
            *self.rule_rows(ESSENCE_RULES),
            "### Mood",
            "",
            f"{self.glossary[MOOD_TERM]} The mood takes its name from these marks:",
            "",
            *self.rule_rows(moods),
            "### Passions",
            "",
            "The Creator delights in some kinds of deeds. You can reveal the Creator's passions to the sons.",
            "",
            "| Passion | Delights in | Deeds that feed it |",
            "|---|---|---|",
        ]
        for passion, spec in CREATOR_PASSIONS.items():
            deeds = listing(sorted(feeds[passion.value])) if feeds.get(passion.value) else "—"
            lines.append(f"| {spec.label} | {cell(spec.hint)} | {deeds} |")
        return [*lines, ""]

    def doom(self) -> list[str]:
        return [
            "## The doom clock",
            "",
            f"{self.glossary[DOOM_TERM]}",
            "",
            f"When doom comes, it takes one of the shapes listed under [Shapes of the end]({TERMS}#k-shapes-of-the-end) "
            "in *The Things of the World and Their Names*.",
            "",
            *self.rule_rows(DOOM_RULES),
        ]


def broken_links(text: str) -> list[str]:
    anchors = set(ANCHOR.findall(text))
    headings = {re.sub(r"[^a-z0-9 -]", "", line.lstrip("#").strip().lower()).replace(" ", "-") for line in text.splitlines() if line.startswith("## ")}
    return sorted({target for target in LINK.findall(text) if target not in anchors and target not in headings})


def missing_entries(text: str) -> list[str]:
    anchors = set(ANCHOR.findall(text))
    wanted = {slug("g", key.value) for key in SCENARIOS if key is not CUSTOM} | {slug("h", key.value) for key in ACHIEVEMENTS}
    return sorted(wanted - anchors)


def missing_terms(text: str) -> list[str]:
    companion = ROOT / "docs" / "mechanics" / TERMS
    if not companion.exists():
        return []
    known = set(ANCHOR.findall(companion.read_text(encoding="utf-8")))
    return sorted({target for target in re.findall(rf"\]\({re.escape(TERMS)}#([^)]+)\)", text) if target not in known})


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
    parser = argparse.ArgumentParser(description="Write the booklet of goals, achievements, growth and score, as one Markdown file.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT, help=f"Markdown file to write (default: {DEFAULT_OUTPUT.relative_to(ROOT)})")
    parser.add_argument("--stdout", action="store_true", help="print the Markdown instead of writing a file")
    parser.add_argument("--force", action="store_true", help="replace an existing file that this script did not write")
    arguments = parser.parse_args()
    text = "\n".join(Booklet().lines()).rstrip() + "\n"
    problems = (
        [f"broken link #{target}" for target in broken_links(text)]
        + [f"missing entry #{target}" for target in missing_entries(text)]
        + [f"no section {TERMS}#{target}" for target in missing_terms(text)]
    )
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
    print(f"Wrote {output} ({len(text.encode('utf-8')) / 1024:.0f} KB, {count(len(ACHIEVEMENTS), 'achievement', 'achievements')}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
