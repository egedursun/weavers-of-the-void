from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.node import ActorKind
from aerona.services.books.records import ChangeLine, Ledger

OWNER = 14


def progress(change_id: int, epoch: int, row_key: str, values: tuple[float, float], *, table: str = "son_goals", field: str = "progress") -> ChangeLine:
    return ChangeLine(
        change_id,
        epoch,
        None,
        None,
        None,
        None,
        table,
        field,
        OWNER,
        None,
        LedgerOperation.UPDATE,
        values[0],
        None,
        None,
        values[1],
        None,
        None,
        ActorKind.ENGINE,
        None,
        None,
        row_key,
    )


def test_then_and_now_never_joins_two_rows_of_one_table() -> None:
    ledger = Ledger({OWNER: "Kaldren"})
    ledger.take_change(progress(1, 1, '{"id": 10}', (0, 40)), [])
    ledger.take_change(progress(2, 6, '{"id": 11}', (5, 100)), [])
    assert ledger.then_and_now(OWNER) == []
    lines = ledger.changes_of(OWNER)
    assert len(lines) == 2


def test_a_row_named_by_its_key_is_told_apart() -> None:
    ledger = Ledger({OWNER: "Kaldren"})
    ledger.take_change(progress(1, 2, '{"community_entity_id": 14, "generation_epoch": 2}', (10, 30), table="generations", field="alive"), [])
    ledger.take_change(progress(2, 5, '{"community_entity_id": 14, "generation_epoch": 5}', (50, 70), table="generations", field="alive"), [])
    rows = dict(ledger.then_and_now(OWNER))
    assert set(rows) == {"Alive (generations, generation epoch 2)", "Alive (generations, generation epoch 5)"}
    assert all("generation epoch" in line for line in ledger.changes_of(OWNER))
