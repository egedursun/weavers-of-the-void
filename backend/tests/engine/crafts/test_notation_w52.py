from aerona.catalog.notations import BY_RANK, NOTATIONS
from aerona.db.tables.crafts import NumberSystemRow
from aerona.domain.enums.crafts import Notation
from aerona.engine.crafts.reckoning import numeracy_of
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, people

RULES = Rules()


def test_four_notations_ranked_from_tallies_to_signs_for_unknowns() -> None:
    assert len(Notation) == 4 and set(NOTATIONS) == set(Notation)
    assert BY_RANK == (Notation.TALLY, Notation.ADDITIVE, Notation.POSITIONAL, Notation.SYMBOLIC)
    rates = [getattr(RULES.numeracy, f"{notation.value}_reckoning_pct") for notation in BY_RANK]
    assert rates == sorted(rates) and rates[0] < 100 < rates[-1]


async def test_a_people_reckons_by_its_notation(realm: Realm) -> None:
    folk = await people(realm, "Counters")
    row = NumberSystemRow(people_entity_id=folk.id, base=10, notation=Notation.TALLY, zero=False, numeracy=50, locked=[])
    realm.session.add(row)
    await realm.session.flush()
    tallied = await numeracy_of(realm.session, RULES, folk.id)
    row.notation = Notation.SYMBOLIC
    signed = await numeracy_of(realm.session, RULES, folk.id)
    assert tallied < signed
