from aerona.db.base import Base
from aerona.db.tables.communication import PublicOpinionRow
from aerona.services.books.typed import column_labels


def test_a_value_column_never_shares_its_label_with_the_record_it_names() -> None:
    labels = column_labels(list(PublicOpinionRow.__table__.columns))
    assert labels["subject_node_id"] == "Subject" and labels["subject"] == "Subject kind"


def test_no_table_shows_two_columns_under_one_label() -> None:
    doubled = []
    for table in Base.metadata.sorted_tables:
        labels = list(column_labels(list(table.columns)).values())
        if len(labels) != len(set(labels)):
            doubled.append(table.name)
    assert doubled == []
