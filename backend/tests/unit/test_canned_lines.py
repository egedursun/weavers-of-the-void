import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_canned_lines", REPOSITORY_ROOT / "scripts" / "check_canned_lines.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_canned_lines"] = module
    spec.loader.exec_module(module)
    return module


def test_a_pool_of_canned_sentences_is_caught() -> None:
    source = (
        "FATES = (\n"
        '    "That night the victim fled before dawn",\n'
        '    "A stranger died in the victim\'s place",\n'
        ")\n"
        'SIGNS = (Line("a.1", "one"), Line("a.2", "two"))\n'
        'LABELS = ("grain", "sacred goods")\n'
        "def tell(rng):\n"
        '    return rng.pick(("The sky split above the town", "The wells ran over at dawn"))\n'
    )
    assert [(item.line, item.name) for item in checker().pools({Path("lines.py"): source})] == [(1, "FATES"), (5, "SIGNS"), (8, "rng.pick")]


def test_no_source_keeps_a_pool_of_canned_sentences() -> None:
    module = checker()
    assert module.pools(module.sources()) == []


def test_a_pool_of_sentence_variants_in_pairs_is_caught_and_a_keyed_table_is_not() -> None:
    source = (
        "REWARDS = (\n"
        '    ("Fate gave the god fame: {reason}", "Fate gave the god its fame."),\n'
        '    ("In the mouths of mortals the god grew: {reason}", "In the mouths of mortals the god grew."),\n'
        ")\n"
        'TABLE = (("warning_1", "Leakage crossed its first threshold in {world}.", "horror.first"),\n'
        '    ("warning_2", "Leakage crossed its second threshold in {world}.", "horror.second"))\n'
    )
    assert [(item.line, item.name) for item in checker().pools({Path("lines.py"): source})] == [(1, "REWARDS")]


def test_a_table_of_phrase_variants_is_caught_and_a_pair_of_labels_is_not() -> None:
    source = (
        "PHRASES = {\n"
        '    "narrow": ("when their homeland grew too small", "when their lands grew crowded", "when they no longer fit"),\n'
        '    "hunger": ("when their food ran short", "when hunger came to them", "when famine struck them"),\n'
        "}\n"
        "LABELS = {\n"
        '    "custom": ("the weight of custom", "custom forsaken by all"),\n'
        '    "law": ("the rule of law", "laws that bind no one"),\n'
        "}\n"
    )
    assert [(item.line, item.name) for item in checker().pools({Path("lines.py"): source})] == [(1, "PHRASES")]


def test_a_per_kind_sentence_table_in_a_catalogue_is_caught() -> None:
    module = checker()
    source = (
        "DANGERS = MappingProxyType(\n"
        "    {\n"
        '        DangerSource.BEASTS: DangerSpec("Beasts", "Wild beasts took {count} of {community} in {region}", None),\n'
        '        DangerSource.BANDITS: DangerSpec("Bandits", "Bandits preyed on {community} along the roads of {region}", None),\n'
        "    }\n"
        ")\n"
        'LABELS = MappingProxyType({DangerSource.BEASTS: DangerSpec("Beasts", None), DangerSource.BANDITS: DangerSpec("Bandits", None)})\n'
    )
    assert [(item.line, item.name) for item in module.pools({module.CATALOGUE / "dangers.py": source})] == [(1, "DANGERS")]
    assert module.pools({module.CATALOGUE / "incident_kinds" / "nature.py": source}) == []
