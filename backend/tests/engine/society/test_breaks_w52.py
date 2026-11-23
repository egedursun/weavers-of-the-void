from aerona.catalog.life.mortal import BREAK_TRAITS
from aerona.core.random import RandomKey, SeededRandom
from aerona.db.tables.polity import OfficeRow
from aerona.domain.enums.mortal import StressBreak
from aerona.domain.enums.polity import OfficeKind
from aerona.engine.mortal.acts import BREAKS, come_back, withdraw
from aerona.engine.mortal.profile import ensure_profile
from tests.engine.society.factories import Realm, context, mortal, people


def test_seven_breaks_each_handled() -> None:
    assert set(BREAKS) == set(StressBreak) and StressBreak.WITHDRAWAL in BREAK_TRAITS


async def test_withdrawal_leaves_office_and_ends_with_rest(realm: Realm) -> None:
    regent = await mortal(realm, "Regent")
    realm_folk = await people(realm, "Folk")
    office = OfficeRow(polity_entity_id=realm_folk.id, kind=next(iter(OfficeKind)), holder_entity_id=regent.id, powers=[])
    realm.session.add(office)
    await realm.session.flush()
    ctx = context(realm.session, epoch=3)
    profile, _ = await ensure_profile(realm.session, regent.id, 3)
    broke = await withdraw(ctx, regent, profile, SeededRandom(RandomKey(1, 1, "test")))
    assert broke.key == "stress.withdrawal" and office.holder_entity_id is None
    profile.last_break, profile.last_break_epoch = StressBreak.WITHDRAWAL, 3
    assert not await come_back(ctx, regent, profile, cared=False)
    assert await come_back(context(realm.session, epoch=5), regent, profile, cared=True)
