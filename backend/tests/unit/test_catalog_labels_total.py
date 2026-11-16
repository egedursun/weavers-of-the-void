import enum
import importlib
import pkgutil
from collections.abc import Mapping

import aerona.catalog


def label_maps() -> list[tuple[str, Mapping[enum.Enum, object]]]:
    found = []
    for module in pkgutil.iter_modules(aerona.catalog.__path__):
        loaded = importlib.import_module(f"aerona.catalog.{module.name}")
        for name, value in vars(loaded).items():
            if name.endswith("_LABELS") and isinstance(value, Mapping) and value and isinstance(next(iter(value)), enum.Enum):
                found.append((f"{module.name}.{name}", value))
    return found


def test_every_catalogue_label_map_names_every_value_of_its_enum() -> None:
    gaps = {name: sorted(member.value for member in type(next(iter(table))) if member not in table) for name, table in label_maps()}
    assert {name: missing for name, missing in gaps.items() if missing} == {}
