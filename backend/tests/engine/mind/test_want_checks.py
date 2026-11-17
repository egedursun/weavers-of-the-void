from aerona.db.tables.lore import MessageRow
from aerona.db.tables.polity import OathRow
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, MortalRole
from aerona.domain.enums.mind import LifeGoal, ThoughtKind, WantKind
from aerona.domain.enums.polity import OathKind, OathStatus
from aerona.engine.context import TickContext
from aerona.engine.mind.aspirations import MEASURES, WANT_CHECKS, gone, probe_of
from aerona.engine.mind.thoughts import think
from aerona.engine.primitives.queries import connect
from tests.engine.society.factories import Realm, context, mortal, settlement, son


async def scene(realm: Realm) -> tuple[TickContext, int]:
    ctx = context(realm.session)
    town = await settlement(realm, "Hollin")
    return ctx, town.id


async def test_a_vengeance_is_done_when_its_target_is_gone(realm: Realm) -> None:
    ctx, town = await scene(realm)
    seeker = await mortal(realm, "Sela", location_id=town)
    foe = await mortal(realm, "Tor", location_id=town)
    probe = await probe_of(ctx, seeker, foe.id, 1)
    assert not await gone(probe)
    assert await MEASURES[LifeGoal.AVENGE_KIN](probe) == 33
    foe.status, foe.end_epoch = EntityStatus.DEAD, ctx.epoch
    assert await gone(probe) and await MEASURES[LifeGoal.AVENGE_KIN](probe) == 100
    assert await WANT_CHECKS[WantKind.AVENGE](await probe_of(ctx, seeker, None, 1))


async def test_an_office_a_fine_weapon_a_child_and_a_teacher_meet_their_wants(realm: Realm) -> None:
    ctx, town = await scene(realm)
    knight = await mortal(realm, "Bram", location_id=town, role=MortalRole.SWORN_WARRIOR)
    probe = await probe_of(ctx, knight, None, 1)
    for want in (WantKind.GAIN_OFFICE, WantKind.FINE_WEAPON, WantKind.HAVE_A_CHILD, WantKind.FIND_A_TEACHER, WantKind.VISIT_A_SHRINE, WantKind.WIN_GLORY):
        assert not await WANT_CHECKS[want](probe), want
    await connect(realm.session, knight.id, town, BondKind.RULES, ctx.epoch)
    probe.profile.wealth = 80
    child = await mortal(realm, "Ivo", location_id=town)
    master = await mortal(realm, "Orrin", location_id=town)
    await connect(realm.session, knight.id, child.id, BondKind.PARENT_OF, ctx.epoch)
    await connect(realm.session, knight.id, master.id, BondKind.APPRENTICE_OF, ctx.epoch)
    await think(realm.session, ctx.rules, knight.id, ThoughtKind.WON_DUEL, ctx.epoch, forced=True)
    god = await son(realm.session, "Vael", realm.world.id)
    realm.session.add(MessageRow(epoch=ctx.epoch, sender_node_id=knight.id, recipient_node_id=god.id, intent=MessageIntent.PRAYER, text="Hear me."))
    await realm.session.flush()
    for want in (WantKind.GAIN_OFFICE, WantKind.FINE_WEAPON, WantKind.HAVE_A_CHILD, WantKind.FIND_A_TEACHER, WantKind.VISIT_A_SHRINE, WantKind.WIN_GLORY):
        assert await WANT_CHECKS[want](probe), want


async def test_a_fulfilled_pilgrimage_counts_as_a_shrine_visited(realm: Realm) -> None:
    ctx, town = await scene(realm)
    pilgrim = await mortal(realm, "Seren", location_id=town)
    realm.session.add(OathRow(swearer_entity_id=pilgrim.id, kind=OathKind.PILGRIMAGE, status=OathStatus.FULFILLED, sworn_epoch=1, ended_epoch=ctx.epoch))
    await realm.session.flush()
    assert await WANT_CHECKS[WantKind.VISIT_A_SHRINE](await probe_of(ctx, pilgrim, None, 1))
