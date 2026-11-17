import ast
import re
from string import Formatter
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from incident_sites import SOURCE, Site, appendix_groups, enum_classes, write_sites

TARGET = SOURCE / "catalog" / "incident_kinds"
GROUPS = (
    "single_combat",
    "battles",
    "vessels",
    "body",
    "making",
    "exchange",
    "law",
    "diplomacy",
    "faith",
    "movement",
    "social",
    "knowledge",
    "nature",
    "cosmos",
    "gods",
    "peoples",
)
EXTRA_FAMILIES = {"gods": 15, "player": 15, "diplomacy": 8, "prisoner": 1, "tribute": 8}
TOOL_WORDS = (
    (2, ("war", "army", "unit", "siege", "spies", "defend", "moles", "formation", "commander", "take_arms", "station", "seize")),
    (
        6,
        (
            "trade",
            "barter",
            "buy",
            "lend",
            "lent",
            "repaid",
            "company",
            "shares",
            "insurance",
            "market",
            "money",
            "levy",
            "convoy",
            "ship",
            "corvee",
            "workshop",
            "racket",
            "salvage",
            "charter",
            "bounty",
            "contract",
            "aid",
            "economic",
            "produced",
        ),
    ),
    (
        7,
        (
            "law",
            "pardon",
            "tribunal",
            "appeal",
            "accus",
            "office",
            "mandate",
            "policy",
            "court",
            "claim",
            "title",
            "realm",
            "caste",
            "reform",
            "proclaim",
            "demand",
            "scheme",
            "bribe",
            "register",
            "throne",
            "citizenship",
            "surveillance",
            "estate",
            "leverage",
            "cover_up",
            "leak",
            "mock",
            "turf",
        ),
    ),
    (8, ("diplomacy", "parley", "terms", "fealty", "denied", "backed")),
    (
        9,
        (
            "pray",
            "worship",
            "preach",
            "spirit",
            "offer",
            "curse",
            "foresee",
            "prophes",
            "vision",
            "divin",
            "power",
            "gift",
            "charm",
            "purif",
            "enchant",
            "heroquest",
            "god",
            "sky",
            "end_time",
            "defier",
        ),
    ),
    (10, ("expedition", "explore", "migrat", "route", "escape", "enter_realm", "camp", "road", "confine", "withdraw", "sanctuary", "post", "dispatch")),
    (
        11,
        (
            "dish",
            "game",
            "club",
            "circle",
            "culture",
            "custom",
            "pet",
            "marriage",
            "cooperative",
            "home",
            "legacy",
            "want",
            "norm",
            "honour",
            "care",
            "rescue",
            "speech",
            "words",
            "fear",
            "role",
        ),
    ),
    (
        12,
        (
            "knowledge",
            "learn",
            "teach",
            "decipher",
            "research",
            "theory",
            "school",
            "examination",
            "publish",
            "record",
            "discover",
            "invent",
            "language",
            "tongue",
            "mind",
            "true_name",
            "reckon",
            "secret",
            "relic",
            "programme",
            "network",
            "intrude",
            "kind",
            "method",
            "pattern",
            "line_",
            "sapience",
            "remote",
        ),
    ),
    (
        13,
        (
            "commons",
            "perennial",
            "plant",
            "herd",
            "tame",
            "reserve",
            "poach",
            "land",
            "forecast",
            "season",
            "species",
            "sails",
            "rebuilding",
            "prepare_town",
            "shore_up",
            "hunt",
        ),
    ),
    (4, ("disease", "cure", "organ", "augment", "symbiont", "maimed", "clone", "sample", "sickness", "drill_trait", "grown")),
    (
        5,
        (
            "built",
            "forge",
            "fabricate",
            "draw",
            "design",
            "refit",
            "model",
            "blueprint",
            "structure",
            "build",
            "construct",
            "replicator",
            "make_",
            "ruin",
            "hoard",
            "study",
        ),
    ),
)
ROLE_MAP_SOURCE = SOURCE / "catalog" / "incident_roles.py"
SLUG = re.compile(r"[^a-z0-9]+")
QUOTE_WIDTH = 90


@dataclass
class Gathered:
    key: str
    sites: list[Site] = field(default_factory=list)
    prefix: tuple[str, str] | None = None


def group_of(key: str, families: dict[str, int]) -> int:
    family = key.split(".", 1)[0]
    if family in families:
        return families[family]
    if family in EXTRA_FAMILIES:
        return EXTRA_FAMILIES[family]
    if key.startswith("tools.son."):
        return 15
    if key.startswith("tools.mortal."):
        name = key.split(".", 2)[2]
        return next((group for group, words in TOOL_WORDS if any(word in name for word in words)), 11)
    return 16


def role_maps() -> dict[str, tuple[str, ...]]:
    tree = ast.parse(ROLE_MAP_SOURCE.read_text())
    aliases = {
        node.targets[0].id: node.value.attr
        for node in tree.body
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Attribute) and isinstance(node.targets[0], ast.Name)
    }
    found: dict[str, tuple[str, ...]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values, strict=True):
                if isinstance(key, ast.Constant) and isinstance(value, ast.Tuple):
                    found[key.value] = tuple(
                        aliases.get(item.id, "SUBJECT") if isinstance(item, ast.Name) else item.attr
                        for item in value.elts
                        if isinstance(item, (ast.Name, ast.Attribute))
                    )
    return found


def slug(text: str) -> str:
    words = [part for part in SLUG.split(text.lower()) if part and part not in {"self", "ctx", "name", "value", "row", "await", "len"}]
    return "_".join(words[-2:]) or "value"


def quoted(text: str) -> str:
    if len(text) <= QUOTE_WIDTH:
        return repr(text)
    pieces: list[str] = []
    current = ""
    for word in text.split(" "):
        candidate = f"{current} {word}" if current else word
        if len(candidate) > QUOTE_WIDTH and current:
            pieces.append(current + " ")
            current = word
        else:
            current = candidate
    pieces.append(current)
    return "(" + " ".join(repr(piece) for piece in pieces) + ")"


def braces(text: str) -> str:
    return text.replace("{", "{{").replace("}", "}}")


@cache
def module_strings(path: Path) -> dict[str, str]:
    tree = ast.parse(path.read_text())
    return {
        target.id: node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
        for target in node.targets
        if isinstance(target, ast.Name)
    }


def derive(site: Site, roles: tuple[str, ...]) -> tuple[str, list[tuple[str, str]]]:
    text = site.text
    if isinstance(text, ast.Name) and text.id in module_strings(site.path):
        return braces(module_strings(site.path)[text.id]), []
    if isinstance(text, ast.Constant) and isinstance(text.value, str):
        if site.via == "line":
            fields = sorted({name for _, name, _, _ in Formatter().parse(text.value) if name})
            return text.value, [(name.split("[")[0].split(".")[0], "name") for name in fields]
        return braces(text.value), []
    if not isinstance(text, ast.JoinedStr):
        return "", []
    ids = list(site.ids)
    counts = Counter(roles)
    parts: list[str] = []
    found: list[tuple[str, str]] = []
    for part in text.values:
        if isinstance(part, ast.Constant):
            parts.append(braces(str(part.value)))
            continue
        if not isinstance(part, ast.FormattedValue):
            continue
        value = part.value
        if isinstance(value, ast.Attribute) and value.attr == "name" and f"{ast.unparse(value.value)}.id" in ids:
            position = ids.index(f"{ast.unparse(value.value)}.id")
            spread = [*roles, *["SUBJECT"] * max(0, len(ids) - len(roles))]
            role = spread[position]
            occurrence = spread[: position + 1].count(role) - 1
            many = spread.count(role) > 1 or counts[role] > 1
            parts.append(f"{{{role.lower()}[{occurrence}]}}" if many else f"{{{role.lower()}}}")
            continue
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "several" and len(value.args) == 3:
            key = slug(ast.unparse(value.args[0]))
            one, many = (ast.literal_eval(arg) if isinstance(arg, ast.Constant) else "item" for arg in value.args[1:])
            parts.append(f"{{{key}:{one}|{many}}}")
            found.append((key, "count"))
            continue
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "spoken" and value.args:
            key = slug(ast.unparse(value.args[0]))
            parts.append(f"{{{key}}}")
            found.append((key, "enum"))
            continue
        if isinstance(value, ast.Attribute) and value.attr == "name":
            key = slug(ast.unparse(value.value))
            parts.append(f"{{{key}}}")
            found.append((key, "node"))
            continue
        key = slug(ast.unparse(value))
        parts.append(f"{{{key}}}")
        found.append((key, "number" if part.format_spec is None and not isinstance(value, ast.JoinedStr) else "name"))
    return "".join(parts), found


FACT_VALUES = {"count": "FactValue.NUMBER", "number": "FactValue.NUMBER", "enum": "FactValue.ENUM", "node": "FactValue.NODE", "name": "FactValue.NAME"}


def render_spec(key: str, gathered: Gathered, roles_of: dict[str, tuple[str, ...]], group: str, enum_names: set[str]) -> str:
    sites = sorted(gathered.sites, key=lambda site: (site.via != "line", site.where))
    base_key = gathered.prefix[0] if gathered.prefix else key
    roles = roles_of.get(base_key) or roles_of.get(key) or ()
    template, guessed = derive(sites[0], roles) if sites else ("", [])
    if gathered.prefix:
        template = template or ""
    role_specs = []
    seen: set[str] = set()
    for role in roles:
        if role in seen:
            continue
        seen.add(role)
        many = roles.count(role) > 1
        role_specs.append(f"RoleSpec(R.{role}, required=False{', many=True' if many else ''})")
    widest = max((len(site.ids) for site in sites), default=0)
    if widest > len(roles):
        if "SUBJECT" in seen:
            role_specs = [spec.replace("RoleSpec(R.SUBJECT, required=False)", "RoleSpec(R.SUBJECT, required=False, many=True)") for spec in role_specs]
        else:
            role_specs.append("RoleSpec(R.SUBJECT, required=False, many=True)")
    facts: list[str] = []
    named: set[str] = set()
    for fact, kind in guessed:
        if fact in named or fact.upper() in seen:
            continue
        named.add(fact)
        unit = ", unit=FactUnit.COUNT" if kind == "count" else ""
        facts.append(f"FactSpec({fact!r}, {FACT_VALUES[kind]}{unit}, required=False)")
    kinds = Counter(site.chronicle_kind for site in sites if site.chronicle_kind)
    feeds = Counter(site.feed for site in sites if site.feed)
    magnitudes = Counter(site.magnitude for site in sites if site.magnitude)
    values = [repr(base_key), f"G.{group.upper()}", quoted(template)]
    if role_specs:
        values.append(f"roles=({', '.join(role_specs)},)")
    if facts:
        values.append(f"facts=({', '.join(facts)},)")
    if any(site.has_place for site in sites):
        values.append("place=PlaceRule.WHEN_KNOWN")
    if kinds:
        values.append(f"chronicle_kind=K.{kinds.most_common(1)[0][0].upper()}")
    if feeds:
        values.append(f"feed=F.{feeds.most_common(1)[0][0].upper()}")
    if magnitudes:
        values.append(f"magnitude={magnitudes.most_common(1)[0][0]}")
    values.append("draft=True")
    spec = f"IncidentKindSpec({', '.join(values)})"
    if gathered.prefix:
        enum_names.add(gathered.prefix[1])
        return f"*per_value({gathered.prefix[0]!r}, {gathered.prefix[1]}, {spec}),"
    return f"{spec},"


def gather(sites: list[Site]) -> dict[str, Gathered]:
    domain = {name for name, enum in enum_classes().items() if enum.__module__.startswith("aerona.domain.enums.")}
    found: dict[str, Gathered] = {}
    covered: set[str] = set()
    for site in sites:
        if site.enum_prefix and site.enum_prefix[1] in domain:
            prefix = f"{site.enum_prefix[0]}*"
            entry = found.setdefault(prefix, Gathered(prefix, prefix=site.enum_prefix))
            entry.sites.append(site)
            covered |= set(site.keys)
    for site in sites:
        for key in site.keys:
            if key in covered:
                continue
            found.setdefault(key, Gathered(key)).sites.append(site)
    return found


def phase_names() -> list[str]:
    sys.path.insert(0, str(SOURCE.parent))
    from aerona.engine.pipeline import PHASE_REGISTRY

    return sorted(PHASE_REGISTRY)


def write_phases() -> str:
    phases = phase_names()
    path = TARGET / "phases.py"
    path.write_text(
        "from aerona.catalog.incident_kinds.spec import IncidentKindSpec\n"
        "from aerona.domain.enums.records import PlaceRule, ProcessClock\n"
        "from aerona.domain.enums.records import ProcessGroup as G\n\n"
        f"PHASE_NAMES: tuple[str, ...] = ({''.join(repr(name) + ', ' for name in phases)})\n\n"
        "KINDS: tuple[IncidentKindSpec, ...] = tuple(\n"
        '    IncidentKindSpec(f"phase.{name}", G.PEOPLES, "", place=PlaceRule.NONE, clock=ProcessClock.PHASE, told=False) for name in PHASE_NAMES\n'
        ")\n"
    )
    return str(path)


def main() -> None:
    if "--phases-only" in sys.argv:
        ruff = SOURCE.parent.parent / ".venv" / "bin" / "ruff"
        written = write_phases()
        subprocess.run([str(ruff), "format", "-q", written], check=False)
        print(f"{len(phase_names())} phase kinds")
        return
    if "--all" not in sys.argv:
        raise SystemExit("The group modules are owned by hand now; pass --phases-only, or --all to overwrite every group module.")
    sites = write_sites()
    families = appendix_groups()
    roles_of = role_maps()
    gathered = gather(sites)
    modules: dict[int, list[str]] = defaultdict(list)
    enums_by_module: dict[int, set[str]] = defaultdict(set)
    for key, entry in sorted(gathered.items()):
        group = group_of(entry.prefix[0] if entry.prefix else key, families)
        modules[group].append(render_spec(key, entry, roles_of, GROUPS[group - 1], enums_by_module[group]))
    classes = enum_classes()
    TARGET.mkdir(exist_ok=True)
    for number, name in enumerate(GROUPS, start=1):
        body = "\n".join(f"    {line}" for line in modules.get(number, []))
        enum_imports = defaultdict(set)
        for enum_name in enums_by_module.get(number, set()):
            enum_imports[classes[enum_name].__module__].add(enum_name)
        imports = "\n".join(f"from {module} import {', '.join(sorted(names))}" for module, names in sorted(enum_imports.items()))
        text = (
            "from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec, RoleSpec, per_value\n"
            "from aerona.domain.enums.chronicle import ChronicleKind as K\n"
            "from aerona.domain.enums.chronicle import FeedCategory as F\n"
            "from aerona.domain.enums.modifier import IncidentRole as R\n"
            "from aerona.domain.enums.records import FactUnit, FactValue, PlaceRule\n"
            "from aerona.domain.enums.records import ProcessGroup as G\n"
            f"{imports}\n\n"
            f"KINDS: tuple[IncidentKindSpec, ...] = (\n{body}\n)\n"
        )
        path = TARGET / f"g{number:02d}_{name}.py"
        path.write_text(text)
    files = [str(TARGET / f"g{number:02d}_{name}.py") for number, name in enumerate(GROUPS, start=1)] + [write_phases()]
    ruff = SOURCE.parent.parent / ".venv" / "bin" / "ruff"
    subprocess.run([str(ruff), "check", "--fix", "-q", *files], check=False)
    subprocess.run([str(ruff), "format", "-q", *files], check=False)
    print(f"{sum(len(lines) for lines in modules.values())} kinds in {len(GROUPS)} modules")


if __name__ == "__main__":
    main()
