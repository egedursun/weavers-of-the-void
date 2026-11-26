from aerona.db.ledger_capture import UNCAPTURED_TABLES
from aerona.db.tables.divine_will import DivineWillChunkRow
from aerona.engine.recording.checkpoints import captured_tables


def test_the_divine_will_index_store_is_neither_recorded_nor_checkpointed() -> None:
    name = DivineWillChunkRow.__tablename__
    assert name in UNCAPTURED_TABLES
    assert name not in {table.name for table in captured_tables()}
