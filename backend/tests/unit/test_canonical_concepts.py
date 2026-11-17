import importlib
import inspect
import pkgutil
from enum import StrEnum

import aerona.domain.enums
from aerona.catalog.canonical import CANONICAL, RETIRED, parallel_enums


def domain_enums() -> dict[str, type[StrEnum]]:
    found: dict[str, type[StrEnum]] = {}
    for module in pkgutil.iter_modules(aerona.domain.enums.__path__):
        loaded = importlib.import_module(f"aerona.domain.enums.{module.name}")
        for name, value in vars(loaded).items():
            if inspect.isclass(value) and issubclass(value, StrEnum) and value.__module__ == loaded.__name__:
                found[name] = value
    return found


def test_every_concept_names_one_canonical_enum_that_exists() -> None:
    enums = domain_enums()
    assert all(enums.get(kind.__name__) is kind for kind in CANONICAL.values())
    assert set(RETIRED) <= set(CANONICAL)


def test_no_retired_parallel_enum_is_defined_again() -> None:
    assert parallel_enums(domain_enums()) == []


def test_a_second_enum_for_a_concept_is_found() -> None:
    assert parallel_enums([*domain_enums(), "FolkDiet", "DwellingKind"]) == ["DwellingKind", "FolkDiet"]
    assert parallel_enums(["Diet", "HousingLevel", "Attribute"]) == []
