import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

SOURCE = """
def told(tally, rows, count):
    first = f"{tally.towns} towns were read."
    second = f"{len(rows)} records wait."
    third = f"{count} were freed."
    fourth = f"{several(count, 'town', 'towns')} were read."
    fifth = f"The age {count} of its line."
    sixth = f"{several(count, 'town', 'towns')} of the land were read."
    seventh = f"{several(count, 'town', 'towns')} {agree(count, 'was', 'were')} read."
    return first, second, third, fourth, fifth, sixth, seventh


LINE = "{count} people set out"
SPEC = "{count:person|people} set out"
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_counts", REPOSITORY_ROOT / "scripts" / "check_counts.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_counts"] = module
    spec.loader.exec_module(module)
    return module


def test_a_count_written_before_a_plural_word_is_flagged() -> None:
    found = checker().counts({Path("module.py"): SOURCE})
    assert sorted((item.line, item.text) for item in found) == [
        (3, "{tally.towns} towns"),
        (4, "{len(rows)} records"),
        (5, "{count} were"),
        (6, "{several(count, 'town', 'towns')} were"),
        (8, "{several(count, 'town', 'towns')} of the land were"),
        (13, "{count} people"),
    ]


def test_a_screen_count_written_before_a_plural_word_is_flagged() -> None:
    screen = (
        "const a = `${rows.length} records`\n"
        "const b = `${plural(rows.length, 'record', 'records')}`\n"
        "const c = `${row.total} of them`\n"
        "const d = `${row.marriages} marriages`\n"
        "const e = `${formatNumber(nodes)} nodes`\n"
        "const f = `${traveller} turns back`\n"
        "const g = `${fixed(row.mass)} suns`\n"
        "const h = `${plural(sons, 'son', 'sons')} are waiting`\n"
        "const i = `${plural(sons, 'son', 'sons')} ${agree(sons, 'is', 'are')} waiting`\n"
    )
    found = [(item.line, item.text) for item in checker().on_screen({Path("Panel.tsx"): screen})]
    assert found == [(1, "${rows.length} records"), (4, "${row.marriages} marriages"), (5, "${formatNumber(nodes)} nodes"), (8, "plural(…) are")]


def test_every_screen_counts_in_the_singular_and_plural() -> None:
    assert checker().on_screen(checker().screens()) == []


def test_a_count_template_read_by_format_is_flagged() -> None:
    module = checker()
    source = {Path("lines.py"): 'LIVES = "{count:life|lives}"\nPLAIN = "{name} rose"\n'}
    callers = {Path("use.py"): "lines.LIVES.format(count=2)\nPLAIN.format(name='x')\nfill(lines.LIVES, count=2)\n"}
    assert [(item.line, item.text) for item in module.formatted(callers, module.spec_templates(source))] == [(1, "LIVES.format()")]


def test_the_backend_counts_every_word_in_the_singular_and_plural() -> None:
    module = checker()
    assert module.counts({path: path.read_text(encoding="utf-8") for path in sorted(module.SOURCE.rglob("*.py"))}) == []


SCOPED = """
async def keep(ctx):
    laid = 0
    laid += 1
    echoes = await seed(ctx)
    note(f"The admiralty laid down {laid} new ships.")
    note(f"{echoes} great lives will echo.")
    note(f"{laid} in reparations")


async def seed(ctx) -> int:
    return 2
"""


def test_a_counted_name_before_an_adjective_and_a_plural_word_is_flagged() -> None:
    found = checker().counts({Path("module.py"): SCOPED})
    assert sorted(item.text for item in found) == ["{echoes} great lives", "{laid} new ships"]


def test_a_jinja_count_before_its_own_plural_noun_is_flagged() -> None:
    source = (
        "class Result:\n"
        '    SEEN = "You have {{ followers }} followers and {{ renown }} renown."\n'
        "    FINE = \"You have {{ followers | several('follower', 'followers') }}.\"\n"
    )
    found = checker().counts({Path("module.py"): source})
    assert [item.text for item in found] == ["{{ followers }} followers"]


def test_a_name_counted_by_several_before_a_plural_verb_is_flagged() -> None:
    source = (
        "def told(lore: int) -> str:\n"
        "    tales = several(lore, 'tale', 'tales')\n"
        "    kept = several(lore, 'tale', 'tales')\n"
        '    return f\'{tales} were half-remembered and {kept} {agree(lore, "was", "were")} kept\'\n'
    )
    found = checker().counts({Path("module.py"): source})
    assert [item.text for item in found] == ["{tales} were"]


def test_a_template_count_before_a_plural_word_is_caught() -> None:
    module = checker()
    line = "you used {{ line.tool }} {{ line.uses }} times; {{ world_name }} cosmos; {{ line.epochs | several('age', 'ages') }}"
    found = [(field, word) for field, word in module.TEMPLATE_COUNT.findall(line) if module.plural(word) and not module.named(field)]
    assert found == [("line.uses", "times")]


def test_a_jinja_number_in_a_python_string_before_a_plural_word_is_flagged() -> None:
    source = (
        "class Result:\n"
        '    GATHERED = "{{ count }} stars are gathered into {{ name }}."\n'
        '    COST = "Costs {{ rules.son_tools.create_galaxy_ap }} actions."\n'
        '    NAMED = "{{ town }} fabricates goods."\n'
        "    FINE = \"{{ name }} gathers {{ count | several('star', 'stars') }}.\"\n"
    )
    found = checker().counts({Path("module.py"): source})
    assert sorted(item.text for item in found) == ["{{ count }} stars", "{{ rules.son_tools.create_galaxy_ap }} actions"]


def test_a_single_brace_count_before_its_own_plural_noun_is_flagged() -> None:
    source = 'LINE = "Ice closed the waters for {months} months."\nFINE = "Ice closed the waters for {months:month|months}."\n'
    found = checker().counts({Path("module.py"): source})
    assert [item.text for item in found] == ["{months} months"]


def test_a_template_count_before_an_adjective_and_a_plural_word_is_flagged() -> None:
    source = 'LINE = "{count} sensed worlds born"\nFINE = "{count:sensed world|sensed worlds} born"\n'
    found = checker().counts({Path("module.py"): source})
    assert [item.text for item in found] == ["{count} sensed worlds"]
