from aerona.db.base import Base
from aerona.db.read_memo import table_names
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow


def test_a_memo_over_a_node_kind_watches_the_shared_node_table_too() -> None:
    assert table_names((EntityRow,)) == {"nodes", "entities"}
    assert table_names((SonRow,)) == {"nodes", "sons"}


def test_every_mapped_class_is_watched_through_every_table_it_spans() -> None:
    missing = {
        mapper.class_.__name__: sorted(set(mapper_tables) - table_names((mapper.class_,)))
        for mapper in Base.registry.mappers
        if (mapper_tables := {table.name for table in mapper.tables if hasattr(table, "name")}) - table_names((mapper.class_,))
    }
    assert missing == {}
