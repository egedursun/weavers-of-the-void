from aerona.core.grammar import singular
from aerona.db.base import Base
from aerona.services.books.typed import words


def test_a_plural_table_name_reads_as_one_of_its_records() -> None:
    assert singular("ledger entries") == "ledger entry"
    assert singular("theodicy crises") == "theodicy crisis"
    assert singular("doctrine afterlives") == "doctrine afterlife"
    assert singular("treaty clauses") == "treaty clause"
    assert singular("trade route losses") == "trade route loss"
    assert singular("age echoes") == "age echo"
    assert singular("cosmos") == "cosmos"
    assert singular("research focus") == "research focus"


def test_no_table_name_reads_as_a_broken_word() -> None:
    broken = sorted(
        name
        for name in Base.metadata.tables
        if singular(words(name).lower()).endswith(("ie", "caus", "claus", "hous", "crise", "biase", "prosthese", "cosmo", "afterlive"))
    )
    assert not broken, broken
