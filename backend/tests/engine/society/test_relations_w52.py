from sqlalchemy import select

from aerona.catalog.relations import DUTY_RELATIONS, INHERITING_RELATIONS, RELATIONS
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.relations import RelationshipRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.enums.relations import RelationType
from aerona.engine.mortal.kin import fosterers_of
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.records import heir_of
from aerona.engine.relations.book import Facts, derive
from aerona.engine.relations.ties import TieTally, foster_hostage, keep_promises
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, mortal, settlement

RULES = Rules()


def bond(holder: int, subject: int, friendship: int = 0, kinds: list[str] | None = None) -> RelationshipRow:
    return RelationshipRow(
        holder_node_id=holder,
        subject_node_id=subject,
        friendship=friendship,
        romance=0,
        familiarity=0,
        rivalry=0,
        kinds=kinds or [],
        since_epoch=1,
        last_epoch=1,
        locked=[],
    )


def test_twenty_one_relation_types_each_with_floor_duties_and_ending() -> None:
    assert len(RELATIONS) == len(RelationType) == 21
    assert {RelationType.SWORN_KIN, RelationType.FOSTER, RelationType.BETROTHED} <= DUTY_RELATIONS
    assert {RelationType.SWORN_KIN, RelationType.FOSTER} <= INHERITING_RELATIONS
    assert all(spec.ends for spec in RELATIONS.values())


def test_promises_oaths_and_raising_become_standing_types() -> None:
    row = bond(1, 2)
    assert derive(RULES, row, None, Facts(betrothed={2}), best=False) >= {RelationType.BETROTHED}
    assert derive(RULES, row, None, Facts(betrothed={2}, spouses={2}), best=False).isdisjoint({RelationType.BETROTHED})
    assert RelationType.SWORN_KIN in derive(RULES, row, None, Facts(sworn={2}), best=False)
    assert RelationType.FOSTER in derive(RULES, row, None, Facts(fostered={2}), best=False)


async def test_a_soured_promise_breaks_and_grieves_both_houses(realm: Realm) -> None:
    first, second = await mortal(realm, "Ama"), await mortal(realm, "Bren")
    await connect(realm.session, first.id, second.id, BondKind.BETROTHED_TO, 1)
    realm.session.add_all([bond(first.id, second.id, friendship=-60), bond(second.id, first.id, friendship=-10)])
    await realm.session.flush()
    tally = TieTally()
    await keep_promises(context(realm.session), tally)
    await realm.session.flush()
    assert tally.broken == 1
    promise = await realm.session.scalar(select(BondRow).where(BondRow.kind == BondKind.BETROTHED_TO))
    assert promise is not None and promise.state is not BondState.ACTIVE
    assert "relation.betrothal_broken" in set(await realm.session.scalars(select(IncidentRow.kind)))


async def test_a_young_hostage_is_fostered_by_the_house_that_keeps_it(realm: Realm) -> None:
    town = await settlement(realm, "Keep")
    lord, child = await mortal(realm, "Lord"), await mortal(realm, "Child", age=8)
    realm.session.add(MortalProfileRow(entity_id=child.id, life_stage=LifeStage.CHILD, locked=[]))
    await connect(realm.session, lord.id, town.id, BondKind.RULES, 1)
    await realm.session.flush()
    assert await foster_hostage(realm.session, child, town.id, 3)
    assert lord.id in await fosterers_of(realm.session, child.id)


async def test_sworn_kin_inherit_where_no_blood_heir_remains(realm: Realm) -> None:
    dead, sworn = await mortal(realm, "Dead"), await mortal(realm, "Sworn")
    realm.session.add(bond(dead.id, sworn.id, friendship=80, kinds=[RelationType.SWORN_KIN.value]))
    await realm.session.flush()
    dead.location_id = None
    heir = await heir_of(realm.session, dead)
    assert heir is not None and heir.id == sworn.id
