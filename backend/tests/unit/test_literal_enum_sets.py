import importlib.util
from pathlib import Path
from types import ModuleType

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "check_literal_enum_sets.py"

SAMPLE = """
from aerona.domain.enums.environment import TerrainKind as T
from aerona.domain.enums.body import BodyPart
WOODS = frozenset({T.FOREST, T.JUNGLE})
WIDTH = {T.PLAIN: 160}
ONE = frozenset({T.FOREST})
LIMBS = (BodyPart.LEFT_ARM, BodyPart.RIGHT_ARM)
REACH = {BodyPart.LEFT_ARM: 2}
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_literal_enum_sets", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_literal_set_or_mapping_of_a_family_is_caught_outside_its_catalogue() -> None:
    check = checker()
    found = check.literals_in("engine/sample.py", SAMPLE, check.FAMILIES)
    assert sorted((item.line, item.family, item.shape) for item in found) == [
        (4, "terrain", "collection"),
        (5, "terrain", "mapping"),
        (7, "body", "collection"),
    ]
    assert check.literals_in("catalog/terrain.py", SAMPLE, tuple(family for family in check.FAMILIES if family.name == "terrain")) == []


TABLES = """
from aerona.domain.enums.mind import ValueAxis
from aerona.core.total import total, partial
WEIGHTS = {ValueAxis.PIETY: 10, ValueAxis.MARTIAL: 20}
LEAN = total(ValueAxis, {ValueAxis.PIETY: frozenset({ValueAxis.MARTIAL, ValueAxis.LAW})})
SOME = partial(ValueAxis, {ValueAxis.PIETY: 1}, without=(ValueAxis.MARTIAL, ValueAxis.LAW))


def pious(value): return value


def martial(value): return value


ACTS = {ValueAxis.PIETY: pious, ValueAxis.MARTIAL: martial}


def mix(values):
    return {ValueAxis.PIETY: values.piety, ValueAxis.MARTIAL: values.martial}
"""


def test_only_static_tables_outside_a_catalogue_are_caught() -> None:
    check = checker()
    found = check.literals_in("engine/sample.py", TABLES, check.FAMILIES)
    assert [(item.line, item.shape) for item in found] == [(4, "mapping")]


def test_the_source_keeps_every_family_in_its_catalogues() -> None:
    assert checker().main([]) == 0


STORED_KEYS = """
from aerona.domain.enums.relations import RelationType
from aerona.domain.enums.mind import Emotion
RIVALS = frozenset({RelationType.RIVAL.value, RelationType.ENEMY.value})
FEARFUL = {Emotion.FEAR.value, Emotion.ANXIETY.value}
ONE = frozenset({Emotion.FEAR.value})
"""


def test_a_set_of_stored_member_values_is_caught_like_a_set_of_members() -> None:
    check = checker()
    found = check.literals_in("engine/sample.py", STORED_KEYS, check.FAMILIES)
    assert sorted((item.line, item.family, item.enum) for item in found) == [(4, "life", "RelationType"), (5, "life", "Emotion")]
