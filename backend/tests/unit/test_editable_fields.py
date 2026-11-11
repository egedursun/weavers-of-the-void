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
)


def test_every_column_of_a_record_the_god_edits_is_in_its_editor() -> None:
    missing = {
        kind.__tablename__: sorted(
            column.name
            for column in kind.__table__.columns
            if not column.primary_key and column.name != "locked" and column.name not in fields and column.name not in derived
        )
        for kind, fields, derived in EDITORS
    }
    assert {table: columns for table, columns in missing.items() if columns} == {}
