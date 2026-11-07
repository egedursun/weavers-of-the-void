import re
from collections import Counter
from pathlib import Path

import pytest

from aerona.rules.groups import RuleGroup
from aerona.rules.registry import Rules
from aerona.rules.snapshot import catalog

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "aerona"
FRONTEND_ROOT = Path(__file__).resolve().parents[3] / "frontend" / "src"
FRONTEND_SUFFIXES = frozenset({".ts", ".tsx"})
SKIPPED_FRONTEND_PARTS = frozenset({"generated", "node_modules"})
REGISTRY_ROOT = SOURCE_ROOT / "rules" / "registry"
LEGACY_VOCABULARY = SOURCE_ROOT / "migration" / "legacy" / "schema_map.json"
SOURCE_SUFFIXES = frozenset({".py", ".j2", ".json", ".yaml"})
DESCRIPTORS = catalog(Rules())


SKIPPED_BACKEND_PARTS = frozenset({".mypy_cache", "__pycache__", ".ruff_cache"})


def consumer_source() -> str:
    backend = [
        path.read_text(encoding="utf-8")
        for path in SOURCE_ROOT.rglob("*")
        if path.is_file()
        and path.suffix in SOURCE_SUFFIXES
        and REGISTRY_ROOT not in path.parents
        and path != LEGACY_VOCABULARY
        and not SKIPPED_BACKEND_PARTS & set(path.parts)
    ]
    frontend = [
        path.read_text(encoding="utf-8")
        for path in FRONTEND_ROOT.rglob("*")
        if path.is_file() and path.suffix in FRONTEND_SUFFIXES and not SKIPPED_FRONTEND_PARTS & set(path.parts)
    ]
    return "\n".join(backend + frontend)


def is_read(key: str, words: set[str], quoted: set[str]) -> bool:
    if key in words:
        return True
    cuts = [index + 1 for index, char in enumerate(key) if char == "_"]
    return any(key[:cut] in quoted and key[cut:] in quoted for cut in cuts)


def test_every_rule_key_is_read_by_a_consumer_outside_the_registry() -> None:
    source = consumer_source()
    words = set(re.findall(r"\w+", source))
    quoted = set(re.findall(r'"(\w+)"', source))
    assert [descriptor.path for descriptor in DESCRIPTORS if not is_read(descriptor.key, words, quoted)] == []


def test_every_rule_belongs_to_a_declared_group() -> None:
    groups = {group.value for group in RuleGroup}
    assert [descriptor.path for descriptor in DESCRIPTORS if descriptor.group not in groups] == []


def test_no_two_rules_carry_the_same_meaning() -> None:
    labels = Counter(descriptor.label.lower() for descriptor in DESCRIPTORS)
    assert [label for label, count in labels.items() if count > 1] == []


def test_every_registered_group_is_used() -> None:
    used = {descriptor.group for descriptor in DESCRIPTORS}
    assert [group.value for group in RuleGroup if group.value not in used] == []


@pytest.mark.parametrize(
    "path",
    [
        "creation_base_cost.region",
        "rarities.common_max_turns",
        "context.fate_geography_chars",
        "mortal_agents.agents_per_epoch",
        "server.stream_emit_interval_ms",
        "server.writing_emit_interval_ms",
    ],
)
def test_former_constants_are_registry_tunables(path: str) -> None:
    assert path in {descriptor.path for descriptor in DESCRIPTORS}
