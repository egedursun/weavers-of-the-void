import random

from aerona.db.bond_index import BondLookup
from aerona.db.tables.bonds import BondRow
from aerona.domain.enums.bond import BondKind, BondState

KINDS = list(BondKind)[:6]
STATES = list(BondState)


def by_hand(bonds: list[BondRow], kinds: list[BondKind] | None, states: list[BondState], sources: list[int] | None, targets: list[int] | None) -> list[BondRow]:
    return sorted(
        (
            bond
            for bond in bonds
            if bond.state in states
            and (kinds is None or bond.kind in kinds)
            and (sources is None or bond.source_node_id in sources)
            and (targets is None or bond.target_node_id in targets)
        ),
        key=lambda bond: bond.id,
    )


def test_every_lookup_finds_exactly_the_bonds_a_full_scan_finds_as_bonds_come_move_and_go() -> None:
    chance = random.Random(11)
    lookup = BondLookup()
    bonds: list[BondRow] = []
    for number in range(1, 400):
        bond = BondRow(
            id=number, source_node_id=chance.randint(1, 12), target_node_id=chance.randint(1, 12), kind=chance.choice(KINDS), state=chance.choice(STATES)
        )
        bonds.append(bond)
        lookup.add(bond)
    for step in range(600):
        if step % 7 == 0:
            gone = bonds.pop(chance.randrange(len(bonds)))
            lookup.remove(gone)
        if step % 5 == 0:
            moved = chance.choice(bonds)
            moved.kind, moved.target_node_id = chance.choice(KINDS), chance.randint(1, 12)
            lookup.moved(moved)
        kinds = chance.sample(KINDS, chance.randint(1, 3)) if chance.random() < 0.7 else None
        states = chance.sample(STATES, chance.randint(1, len(STATES)))
        sources = [chance.randint(1, 12) for _ in range(chance.randint(1, 3))] if chance.random() < 0.5 else None
        targets = [chance.randint(1, 12) for _ in range(chance.randint(1, 3))] if chance.random() < 0.5 else None
        assert lookup.select(kinds, states, sources, targets) == by_hand(bonds, kinds, states, sources, targets)
