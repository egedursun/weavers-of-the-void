from aerona.db.ledger_capture import RECORD_TABLES, UNCAPTURED_TABLES
from aerona.db.record_edits import RECORD_KEYS
from aerona.services.divine_will.follow import RECORD_CURSORS
from aerona.services.divine_will.passages import indexed_tables


def test_every_table_the_index_renders_by_row_reaches_the_change_record() -> None:
    assert sorted(set(indexed_tables()) & UNCAPTURED_TABLES) == []


def test_every_record_table_the_index_reads_is_followed_for_new_rows_and_for_edits() -> None:
    followed = {name for name, _row, _column in RECORD_CURSORS}
    assert followed == set(RECORD_KEYS)
    assert sorted(followed - RECORD_TABLES - {"chronicle_entities"}) == []
