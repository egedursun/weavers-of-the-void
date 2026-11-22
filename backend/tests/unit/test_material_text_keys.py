import importlib.util
from pathlib import Path

import sqlalchemy as sa

from aerona.constants.materials import MATERIAL_KEY_JSON_COLUMNS, MATERIAL_TEXT_COLUMNS, RENAMED_MATERIALS
from aerona.db.base import Base
from aerona.db.tables import ItemProfileRow
from aerona.domain.enums.material import MaterialKind
from aerona.engine.economy.materials import key_parts, material_kind

MIGRATION = Path(__file__).resolve().parents[2] / "src" / "aerona" / "db" / "alembic" / "versions" / "5d0b7e3a9c21_w52_material_text_keys.py"
KEY_WORDS = ("material", "metal", "feedstock")


def text_material_columns() -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for table in Base.metadata.sorted_tables:
        for column in table.columns:
            plain_text = isinstance(column.type, sa.String) and not isinstance(column.type, sa.Enum)
            if plain_text and any(word in column.name for word in KEY_WORDS):
                found.add((table.name, column.name))
    return found


def test_an_old_material_key_still_reads_as_its_new_name() -> None:
    assert key_parts("bone") == (MaterialKind.CALCIFIED_TISSUE, None)
    assert key_parts("salt") == (MaterialKind.HALITE, None)
    assert material_kind("salt") is MaterialKind.HALITE


def test_every_renamed_material_lands_on_a_current_one() -> None:
    current = {kind.value for kind in MaterialKind}
    for was, now in RENAMED_MATERIALS.items():
        assert was not in current
        assert now in current


def test_every_text_column_holding_a_material_key_is_moved_on_a_rename() -> None:
    assert (ItemProfileRow.__tablename__, "material") in MATERIAL_TEXT_COLUMNS
    assert text_material_columns() == set(MATERIAL_TEXT_COLUMNS)
    spec = importlib.util.spec_from_file_location("material_text_keys", MIGRATION)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert set(migration.TEXT_COLUMNS) == set(MATERIAL_TEXT_COLUMNS)
    assert dict(RENAMED_MATERIALS) == migration.RENAMED
    assert set(migration.JSON_KEY_COLUMNS) == set(MATERIAL_KEY_JSON_COLUMNS)
