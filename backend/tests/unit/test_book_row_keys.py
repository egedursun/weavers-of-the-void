import json

from aerona.services.books.records import RECORD_TABLES, Bindings, Ledger

TOWN = 1007
GOD = 11
GUEST = 112
GATHERING = 1
WORLD = 25


def bound(text: str, records: dict[tuple[int, int], str]) -> str:
    return Bindings({TOWN: "Dorvan", GOD: "Kreaton"}, {}, frozenset(), {}, {}, records).bind(text)


def test_a_row_key_names_its_nodes_records_and_values_never_their_raw_ids_or_keys() -> None:
    ledger = Ledger({TOWN: "Dorvan", GOD: "Kreaton"})
    assert ledger.row_text("divine_debts", json.dumps({"community_entity_id": TOWN, "god_node_id": GOD}), GOD) == "community Dorvan"
    feast = (RECORD_TABLES.index("gatherings"), GATHERING)
    told = ledger.row_text("gathering_guests", json.dumps({"gathering_id": GATHERING, "node_id": GUEST}), GUEST)
    assert bound(told, {feast: "the feast held by Dorvan in year 186"}) == "the feast held by Dorvan in year 186"
    assert bound(told, {}) == "a gathering no longer kept"
    assert ledger.row_text("subsystem_tensions", json.dumps({"subsystem": "death_work", "world_id": WORLD}), WORLD) == "subsystem death work"
