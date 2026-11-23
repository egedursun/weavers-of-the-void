from aerona.catalog.conditions import MAIMS
from aerona.db.tables.body import MaimedCohortRow
from aerona.domain.enums.body import BodyPart, MaimedKind
from aerona.engine.body.cohorts import labour_factor, shooting_factor
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, settlement

RULES = Rules()


def test_eleven_maims_and_the_new_two_aim_at_their_parts() -> None:
    assert len(MaimedKind) == len(MAIMS) == 11
    assert MAIMS[MaimedKind.PARALYSED].part is BodyPart.SPINE and MAIMS[MaimedKind.LOST_FINGERS].part is BodyPart.FINGERS
    assert MAIMS[MaimedKind.LOST_FINGERS].loss(RULES.maimed) == RULES.maimed.lost_fingers_craft_cut


async def test_the_paralysed_weigh_more_on_work_than_those_missing_fingers_who_weigh_on_shooting(realm: Realm) -> None:
    ctx = context(realm.session)
    fingers = await settlement(realm, "Bow", population=1000)
    still = await settlement(realm, "Bed", population=1000)
    realm.session.add(MaimedCohortRow(community_entity_id=fingers.id, kind=MaimedKind.LOST_FINGERS, count=100, veterans=100, updated_epoch=1))
    realm.session.add(MaimedCohortRow(community_entity_id=still.id, kind=MaimedKind.PARALYSED, count=100, veterans=100, updated_epoch=1))
    await realm.session.flush()
    assert await labour_factor(ctx, still) < await labour_factor(ctx, fingers) < 1.0
    assert await shooting_factor(ctx, fingers) > 0 == await shooting_factor(ctx, still)
