import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

ENUMS = """
from enum import StrEnum


class Flavour(StrEnum):
    SWEET = "sweet"
    SOUR = "sour"


class Mood(StrEnum):
    CALM = "calm"
"""

LAYERS = """
ENUM_LAYERS = {
    "taste.Flavour": EnumLayer("authored", "category of the dishes", "dishes"),
    "taste.Gone": EnumLayer("closed", "the engine's own distinctions"),
}
"""

TABLES = """
class DishRow(Base):
    __tablename__ = "dishes"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"))
    flavour: Mapped[Flavour] = mapped_column(enum_type(Flavour, "flavour"))
    sweetness: Mapped[int] = mapped_column(default=0)


class PlainRow(Base):
    __tablename__ = "plain"

    id: Mapped[int] = mapped_column(primary_key=True)
    flavour: Mapped[Flavour] = mapped_column(enum_type(Flavour, "flavour"))
"""


def script() -> ModuleType:
    sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("check_kind_layers", REPOSITORY_ROOT / "scripts" / "check_kind_layers.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_kind_layers"] = module
    spec.loader.exec_module(module)
    return module


def folders(tmp_path: Path) -> tuple[Path, Path, Path]:
    enums = tmp_path / "enums"
    tables = tmp_path / "tables"
    enums.mkdir()
    tables.mkdir()
    (enums / "taste.py").write_text(ENUMS, encoding="utf-8")
    (tables / "food.py").write_text(TABLES, encoding="utf-8")
    layers = tmp_path / "enum_layers.py"
    layers.write_text(LAYERS, encoding="utf-8")
    return enums, tables, layers


def test_an_undeclared_enum_and_a_stale_declaration_are_found(tmp_path: Path) -> None:
    check = script()
    enums, _, layers = folders(tmp_path)
    known = check.all_enums(enums)
    declared = check.declared(layers)
    assert sorted(set(known) - set(declared)) == ["taste.Mood"]
    assert sorted(set(declared) - set(known)) == ["taste.Gone"]
    assert declared["taste.Flavour"].table == "dishes"


def test_an_authored_enum_needs_a_kind_table_with_properties_levers_tools_and_screens(tmp_path: Path) -> None:
    check = script()
    _, tables, _ = folders(tmp_path)
    found = check.kind_tables(tables)
    assert found["dishes"].enums == {"Flavour": "flavour"} and found["dishes"].properties == 1 and found["dishes"].linked
    reach = check.Reach(frozenset(), frozenset())
    good = check.Declared("authored", "category of the dishes", "dishes", None)
    shown = check.Surfaces(found, set(), reach, "Flavour", "flavourValues", set())
    hidden = check.Surfaces(found, set(), reach, "", "", set())
    assert check.authored_problems("taste.Flavour", good, shown) == []
    bare = check.Declared("authored", "category", "plain", None)
    assert len(check.authored_problems("taste.Flavour", bare, hidden)) == 4
    nameless = check.Declared("authored", "category", None, None)
    assert check.authored_problems("taste.Flavour", nameless, hidden) == ["is declared authored but names no kind table"]


def test_a_row_of_a_child_table_writes_its_parent_table_too() -> None:
    check = script()
    parents = {"entities": {"nodes"}, "people_rows": {"entities"}}
    assert check.with_parents({"people_rows"}, parents) == {"people_rows", "entities", "nodes"}
    assert check.with_parents({"dishes"}, parents) == {"dishes"}


def test_the_node_table_is_reached_through_the_tools_that_make_entities() -> None:
    check = script()
    assert "nodes" in check.reached().tools


def test_an_enum_column_stored_under_another_name_counts_as_the_kind_tables_category(tmp_path: Path) -> None:
    check = script()
    tables = tmp_path / "tables"
    tables.mkdir()
    (tables / "games.py").write_text(
        "class GameRow(KindRow):\n"
        "    __tablename__ = 'games'\n"
        "    category: Mapped[GameCategory] = mapped_column('kind', enum_type(GameCategory, 'kind'))\n"
        "    violence: Mapped[int] = mapped_column(default=0)\n",
        encoding="utf-8",
    )
    assert check.kind_tables(tables)["games"].enums == {"GameCategory": "category"}


def test_a_layer_whose_reason_names_another_layer_is_found() -> None:
    check = script()
    assert check.contradicts(check.Declared("authored", "closed: physical", "region_environment", None))
    assert not check.contradicts(check.Declared("closed", "closed: physical or typological set, complete", None, None))
    assert not check.contradicts(check.Declared("authored", "dwelling kinds over the housing ladder", "dwelling_kinds", None))
