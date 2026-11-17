import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from aerona.catalog.kinds.defined import DEFINITIONS

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

ENUMS = """
from enum import StrEnum


class Flavour(StrEnum):
    SWEET = "sweet"
    SOUR = "sour"
    BITTER = "bitter"
"""

ENGINE = """
from aerona.domain.enums.taste import Flavour


def taste(dish):
    if dish.flavour is Flavour.SWEET:
        return 1
    return Flavour.SOUR
"""

TABLE = """
from aerona.core.total import total
from aerona.domain.enums.taste import Flavour

SWEETNESS = total(Flavour, {Flavour.SWEET: 3, Flavour.SOUR: 0, Flavour.BITTER: 0})
"""


def script() -> ModuleType:
    sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("check_kind_definitions", REPOSITORY_ROOT / "scripts" / "check_kind_definitions.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_kind_definitions"] = module
    spec.loader.exec_module(module)
    return module


def tree(tmp_path: Path, *files: tuple[str, str]) -> Path:
    source = tmp_path / "aerona"
    (source / "domain" / "enums").mkdir(parents=True)
    (source / "domain" / "enums" / "taste.py").write_text(ENUMS, encoding="utf-8")
    for name, text in files:
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return source


def test_where_each_value_is_checked_and_used_is_found(tmp_path: Path) -> None:
    check = script()
    source = tree(tmp_path, ("engine/taste.py", ENGINE))
    known = {"taste.Flavour": [("SWEET", "sweet"), ("SOUR", "sour"), ("BITTER", "bitter")]}
    found = check.uses(known, {"taste.Flavour"}, source)
    assert found[("taste.Flavour", "SWEET")].checked == {"engine.taste.taste"}
    assert found[("taste.Flavour", "SOUR")].used == {"engine.taste.taste"}
    assert ("taste.Flavour", "BITTER") not in found


def test_an_enum_without_a_full_table_lacks_a_catalogue_and_one_with_it_passes(tmp_path: Path) -> None:
    check = script()
    known = {"taste.Flavour": [("SWEET", "sweet"), ("SOUR", "sour"), ("BITTER", "bitter")]}
    assert "Flavour" not in check.catalogued(tree(tmp_path / "bare", ("engine/taste.py", ENGINE)), known)
    assert "Flavour" in check.catalogued(tree(tmp_path / "full", ("catalog/taste.py", TABLE)), known)


def module_file(place: str) -> Path | None:
    parts = place.split(".")
    source = REPOSITORY_ROOT / "backend" / "src" / "aerona"
    for end in range(len(parts), 0, -1):
        candidate = source.joinpath(*parts[:end]).with_suffix(".py")
        if candidate.exists():
            return candidate
    return None


def test_every_value_of_every_catalogued_enum_is_labelled_and_names_real_places() -> None:
    assert DEFINITIONS
    for name, table in DEFINITIONS.items():
        for value, defined in table.items():
            assert defined.label.strip(), f"{name}.{value}"
            for place in (*defined.checked_by, *defined.used_by):
                home = module_file(place)
                assert home is not None, f"{name}.{value}: {place}"
                assert name.split(".")[1] in home.read_text(encoding="utf-8"), f"{name}.{value}: {place}"
