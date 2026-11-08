from aerona.db.tables.polity import OfficeRow, VassalageRow
from aerona.domain.enums.polity import OfficeKind
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.subjects import SubjectTally, bargain, confirm, yearn
from aerona.engine.primitives.strength import MilitaryStrength
from tests.engine.society.factories import Realm, context, mortal, tuned
from tests.engine.statecraft.test_statecraft import polity


async def subject(realm: Realm, **values: object) -> tuple[VassalageRow, int]:
    lord, _ = await polity(realm, "Lion Throne")
    vassal, core = await polity(realm, "Hart Throne")
    row = VassalageRow(vassal_entity_id=vassal.id, overlord_entity_id=lord.id, locked=[], **values)
    realm.session.add(row)
    await realm.session.flush()
    return row, core.id


async def test_a_vassal_far_from_its_lords_ways_yearns_for_liberty(realm: Realm) -> None:
    ctx = context(realm.session, tuned(statecraft={"liberty_drift_pct": 100}))
    row, _ = await subject(realm, loyalty=0, liberty=0)
    book = await RealmBook.load(realm.session)
    await yearn(ctx, book, await MilitaryStrength.load(realm.session, ctx.rules), row)
    assert row.liberty > 0
    row.locked = ["liberty"]
    held = row.liberty
    row.loyalty = 100
    await yearn(ctx, book, await MilitaryStrength.load(realm.session, ctx.rules), row)
    assert row.liberty == held


async def test_a_strong_vassal_wins_easier_terms_and_a_weak_one_is_refused(realm: Realm) -> None:
    ctx = context(realm.session, tuned(statecraft={"renegotiate_at": 0, "back_down_ratio_pct": 50}))
    row, _ = await subject(realm, tribute_pct=20, liberty=60, loyalty=50)
    book = await RealmBook.load(realm.session)
    strength = await MilitaryStrength.load(realm.session, ctx.rules)
    tally = SubjectTally()
    await bargain(ctx, book, strength, row, tally)
    assert row.tribute_pct == 10 and row.liberty < 60 and tally.renegotiated == 1
    row.locked = ["liberty"]
    await bargain(ctx, book, strength, row, tally)
    assert row.tribute_pct == 5 and row.liberty == 60 - ctx.rules.statecraft.renegotiate_loyalty
    row.locked = []
    stern = context(realm.session, tuned(statecraft={"renegotiate_at": 0, "back_down_ratio_pct": 100000}))
    loyalty = row.loyalty
    await bargain(stern, book, strength, row, tally)
    assert tally.refused == 1 and row.loyalty < loyalty and row.tribute_pct == 5


async def test_a_new_ruler_of_a_vassal_is_confirmed_by_its_lord(realm: Realm) -> None:
    ctx = context(realm.session)
    row, _ = await subject(realm, loyalty=80, confirm_succession=True)
    first = await mortal(realm, "Ysolde")
    realm.session.add(OfficeRow(polity_entity_id=row.vassal_entity_id, kind=OfficeKind.RULER, holder_entity_id=first.id, powers=[], since_epoch=1))
    await realm.session.flush()
    tally = SubjectTally()
    await confirm(ctx, await RealmBook.load(realm.session), row, tally)
    assert row.confirmed_ruler_entity_id == first.id and tally.confirmed == 0
    heir = await mortal(realm, "Ivo")
    office = await realm.session.get(OfficeRow, (await RealmBook.load(realm.session)).realms[row.vassal_entity_id].office(OfficeKind.RULER).id)
    assert office is not None
    office.holder_entity_id = heir.id
    await realm.session.flush()
    loyalty = row.loyalty
    await confirm(ctx, await RealmBook.load(realm.session), row, tally)
    assert row.confirmed_ruler_entity_id == heir.id and tally.confirmed == 1 and row.loyalty > loyalty
