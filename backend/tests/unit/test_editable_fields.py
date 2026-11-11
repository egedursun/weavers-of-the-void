from pathlib import Path

from aerona.db import tables
from aerona.db.base import Base
from aerona.db.tables.arcana import (
    GRAMMAR_FIELDS,
    LAB_TEXT_FIELDS,
    LONGEVITY_FIELDS,
    UPKEEP_FIELDS,
    WARPING_FIELDS,
    LabTextRow,
    LawUpkeepRow,
    LongevityRow,
    RiteGrammarRow,
    WarpingRow,
)
from aerona.db.tables.mythic import (
    GEAS_FIELDS,
    HEROQUEST_FIELDS,
    MANTLING_FIELDS,
    OFFICE_FIELDS,
    SERVITOR_FIELDS,
    CosmicOfficeRow,
    GeasRow,
    HeroquestRow,
    MantlingRow,
    ServitorRow,
)
from aerona.db.tables.tongues import (
    DECIPHER_FIELDS,
    DIVINE_TONGUE_FIELDS,
    POLICY_FIELDS,
    SCRIPT_FIELDS,
    SOUND_CHANGE_FIELDS,
    DecipherWorkRow,
    DivineTongueRow,
    LanguageGrammarRow,
    LanguagePolicyRow,
    ScriptRow,
    SoundChangeRow,
)
from aerona.db.tables.tongues import GRAMMAR_FIELDS as TONGUE_GRAMMAR_FIELDS
from aerona.engine.primitives.edits import FIXED

EDITORS: tuple[tuple[type[Base], tuple[str, ...], frozenset[str]], ...] = (
    (RiteGrammarRow, GRAMMAR_FIELDS, frozenset({"difficulty"})),
    (LabTextRow, LAB_TEXT_FIELDS, frozenset()),
    (WarpingRow, WARPING_FIELDS, frozenset()),
    (LongevityRow, LONGEVITY_FIELDS, frozenset()),
    (LawUpkeepRow, UPKEEP_FIELDS, frozenset()),
    (HeroquestRow, HEROQUEST_FIELDS, frozenset({"quester_entity_id", "collection_id"})),
    (MantlingRow, MANTLING_FIELDS, frozenset()),
    (ServitorRow, SERVITOR_FIELDS, frozenset()),
    (GeasRow, GEAS_FIELDS, frozenset({"bearer_entity_id"})),
    (CosmicOfficeRow, OFFICE_FIELDS, frozenset()),
    (SoundChangeRow, SOUND_CHANGE_FIELDS, frozenset({"language_entity_id"})),
    (LanguageGrammarRow, TONGUE_GRAMMAR_FIELDS, frozenset()),
    (ScriptRow, SCRIPT_FIELDS, frozenset()),
    (DecipherWorkRow, DECIPHER_FIELDS, frozenset()),
    (LanguagePolicyRow, POLICY_FIELDS, frozenset()),
    (DivineTongueRow, DIVINE_TONGUE_FIELDS, frozenset()),
)


def test_every_column_of_a_record_the_god_edits_is_in_its_editor() -> None:
    missing = {
        kind.__tablename__: sorted(
            column.name
            for column in kind.__table__.columns
            if not column.primary_key and column.name not in FIXED and column.name not in fields and column.name not in derived
        )
        for kind, fields, derived in EDITORS
    }
    assert {table: columns for table, columns in missing.items() if columns} == {}


def test_no_editor_offers_a_value_the_store_keeps_for_itself() -> None:
    offered = {
        f"{module.__name__}.{name}": sorted(set(value) & FIXED)
        for module in (getattr(tables, item) for item in dir(tables) if not item.startswith("_"))
        if hasattr(module, "__name__") and module.__name__.startswith("aerona.db.tables.")
        for name, value in vars(module).items()
        if name.endswith("_FIELDS") and isinstance(value, tuple)
    }
    assert {name: keys for name, keys in offered.items() if keys} == {}


def test_no_drawer_editor_offers_a_value_the_store_keeps_for_itself() -> None:
    root = Path(__file__).resolve().parents[3] / "frontend" / "src"
    offered = sorted(
        f"{path.relative_to(root)}: {key}"
        for path in root.rglob("*.tsx")
        if path.is_file()
        for key in FIXED
        if f"key: '{key}'" in path.read_text(encoding="utf-8")
    )
    assert offered == []
