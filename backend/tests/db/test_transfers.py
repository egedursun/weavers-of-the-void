from aerona.db.tables.factions import FactionProfileRow
from aerona.db.write_guard import WRITE_GUARD
from aerona.domain.enums.faction import FactionKind
from aerona.engine.primitives.transfers import move_amount


def purse(node_id: int, treasury: int, locked: list[str] | None = None) -> FactionProfileRow:
    return FactionProfileRow(faction_entity_id=node_id, kind=next(iter(FactionKind)), treasury=treasury, locked=locked or [])


def test_an_amount_moves_whole_between_free_sides() -> None:
    payer, payee = purse(1, 50), purse(2, 5)
    assert move_amount(payer, payee, "treasury", 20)
    assert (payer.treasury, payee.treasury) == (30, 25)


def test_a_locked_side_stops_the_whole_transfer() -> None:
    for payer, payee in ((purse(1, 50, ["treasury"]), purse(2, 5)), (purse(1, 50), purse(2, 5, ["treasury"]))):
        assert not move_amount(payer, payee, "treasury", 20)
        assert (payer.treasury, payee.treasury) == (50, 5)


def test_a_held_node_stops_the_whole_transfer() -> None:
    token = WRITE_GUARD.set(lambda node_id, _key: node_id == 2)
    try:
        payer, payee = purse(1, 50), purse(2, 5)
        assert not move_amount(payer, payee, "treasury", 20)
        assert (payer.treasury, payee.treasury) == (50, 5)
    finally:
        WRITE_GUARD.reset(token)
