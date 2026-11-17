from aerona.domain.enums.entity import EntityFlag, EntityStatus
from aerona.domain.enums.polity import OathBreach, OathKind, OathStatus
from aerona.engine.polity.oaths import break_oath, home_at_oath, lapse, swear
from aerona.engine.primitives.queries import has_flag
from tests.engine.society.factories import Realm, context, mortal, settlement, son, tuned


async def test_breaking_an_oath_sworn_before_a_god_feeds_its_wrath(realm: Realm) -> None:
    ctx = context(realm.session, tuned(oaths={"wrath_curse_chance": 100}))
    town = await settlement(realm, "Hollin")
    swearer = await mortal(realm, "Brann", location_id=town.id)
    lord = await mortal(realm, "Avel", location_id=town.id)
    witness = await son(realm.session, "Vael", realm.world.id)
    essence = witness.essence
    oath = await swear(ctx, swearer, OathKind.FEALTY, recipient_id=lord.id, witness=witness)
    await break_oath(ctx, oath, OathBreach.THRONE_SEIZED)
    assert witness.essence > essence
    assert await has_flag(realm.session, swearer.id, EntityFlag.CURSED)


async def test_a_vengeance_is_kept_when_its_target_falls_and_a_pilgrim_kept_on_leaving_home(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Hollin")
    far = await settlement(realm, "Farwatch")
    avenger = await mortal(realm, "Seren", location_id=town.id)
    foe = await mortal(realm, "Rask", location_id=town.id)
    vow = await swear(ctx, avenger, OathKind.VENGEANCE, recipient_id=foe.id)
    pilgrim = await mortal(realm, "Ilse", location_id=town.id)
    walk = await swear(ctx, pilgrim, OathKind.PILGRIMAGE, recipient_id=None, note_text=str(town.id))
    assert home_at_oath(walk) == town.id
    later = context(realm.session, epoch=ctx.epoch + 1)
    await lapse(later)
    assert vow.status is OathStatus.SWORN and walk.status is OathStatus.SWORN
    foe.status, foe.end_epoch = EntityStatus.DEAD, later.epoch
    pilgrim.location_id = far.id
    await realm.session.flush()
    kept, _ = await lapse(later)
    assert kept == 2 and vow.status is OathStatus.FULFILLED and walk.status is OathStatus.FULFILLED
