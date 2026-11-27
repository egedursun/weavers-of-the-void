from aerona.db.base import Base
from aerona.db.profile_guard import table_name
from aerona.services.books.typed import NAMED_TABLES, REFERENCE_LABELS, TypedIndex, label_of


def test_a_source_key_names_the_record_it_points_at_instead_of_a_table_and_a_number() -> None:
    index = TypedIndex({7: "Hadrasol", 2139: "The Flood of Saral"})
    index.references = {"gatherings": {286: "the wake of Ordrin in epoch 3"}, "battles": {27: "the battle of epoch 6 at Vael Deep"}}
    assert index.source("gathering.286") == "the wake of Ordrin in epoch 3"
    assert index.source("battle:27") == "the battle of epoch 6 at Vael Deep"
    assert index.source("event:2139") == "The Flood of Saral"
    assert index.source("society.famine") == "society famine"
    assert index.source("gathering.999") == "gathering"


def test_gatherings_and_battles_have_their_own_labels() -> None:
    assert {"gatherings", "battles", "incidents"} <= REFERENCE_LABELS.keys()


def test_a_reference_to_a_record_never_falls_back_to_a_table_and_a_number() -> None:
    index = TypedIndex({})
    for mapper in Base.registry.mappers:
        for column in mapper.local_table.columns:
            for foreign in column.foreign_keys:
                if foreign.column.table.name not in NAMED_TABLES:
                    assert not any(character.isdigit() for character in index.reference(column, 4127)), table_name(mapper)
        assert callable(label_of(mapper))
