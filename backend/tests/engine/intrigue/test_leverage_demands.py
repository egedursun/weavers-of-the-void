from aerona.db.tables.polity import OfficeRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.intrigue import HookDemand
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.intrigue.leverage import comply
from aerona.engine.mortal.profile import ensure_profile
from tests.engine.society.factories import Realm, context, make, mortal


async def test_a_pressed_officer_steps_down_from_every_office_not_held(realm: Realm) -> None:
    ctx = context(realm.session)
    holder, target = await mortal(realm, "Holder"), await mortal(realm, "Target")
    crown = await make(realm.session, "Crown", EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    free = [
        OfficeRow(polity_entity_id=crown.id, kind=kind, holder_entity_id=target.id, powers=[], locked=[]) for kind in (OfficeKind.MARSHAL, OfficeKind.HERALD)
    ]
    kept = OfficeRow(polity_entity_id=crown.id, kind=OfficeKind.TREASURER, holder_entity_id=target.id, powers=[], locked=["holder_entity_id"])
    realm.session.add_all([*free, kept])
    await realm.session.flush()
    text = await comply(ctx, holder.id, target.id, HookDemand.STEP_DOWN)
    assert text == "Target gave up 2 offices"
    assert all(row.holder_entity_id is None and row.since_epoch == ctx.epoch for row in free)
    assert kept.holder_entity_id == target.id
    assert await comply(ctx, holder.id, target.id, HookDemand.STEP_DOWN) is None


async def test_a_pressed_mortal_hands_over_wealth_only_when_both_purses_can_take_it(realm: Realm) -> None:
    ctx = context(realm.session)
    amount = ctx.rules.intrigue.support_wealth
    holder, target = await mortal(realm, "Holder"), await mortal(realm, "Target")
    given, _ = await ensure_profile(realm.session, target.id, ctx.epoch)
    taken, _ = await ensure_profile(realm.session, holder.id, ctx.epoch)
    given.wealth, taken.wealth = 50, 20
    assert await comply(ctx, holder.id, target.id, HookDemand.SUPPORT) is not None
    assert given.wealth == 50 - amount and taken.wealth == 20 + amount
    taken.wealth = 100 - amount + 1
    assert await comply(ctx, holder.id, target.id, HookDemand.SUPPORT) is None
    assert given.wealth == 50 - amount and taken.wealth == 100 - amount + 1
    await realm.session.flush()
    given.wealth, taken.wealth = amount - 1, 0
    assert await comply(ctx, holder.id, target.id, HookDemand.SUPPORT) is None
