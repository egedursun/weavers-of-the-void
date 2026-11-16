from sqlalchemy import select

from aerona.db.tables.communication import CipherRow, PublicOpinionRow, SignalLinkRow
from aerona.db.tables.faith import CultHoldingRow
from aerona.db.tables.intrigue import BeliefRow, FavourRow, SecretRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.military import OccupationRow, SpyNetworkRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.communication import DispatchContent, DispatchState, Medium, OpinionSubject, SignalKind, SignalState
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.faith import HoldingKind
from aerona.domain.enums.intrigue import FavourOrigin, IntrigueSecret
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.models.entity_stats import CultStats, PolityStats, StructureStats
from aerona.engine.communication.ciphers import CipherTally, attack
from aerona.engine.communication.dispatches import DispatchTally, tend_dispatches
from aerona.engine.communication.opinion import OpinionTally, mean_approval, sermons, tend_community
from aerona.engine.communication.post import FACTS, send
from aerona.engine.communication.signals import SignalTally, fall_links
from aerona.engine.polity.laws import LawBook
from tests.engine.society.factories import Realm, context, link, make, mortal, settlement, son, tuned


async def test_a_letter_travels_arrives_and_becomes_belief(realm: Realm) -> None:
    ctx = context(realm.session)
    first = await settlement(realm, "Ashgrove")
    second = await settlement(realm, "Brackwater", location_id=realm.far_region.id)
    report = {FACTS: {str(first.id): {"wealth": 40}}}
    row = await send(ctx, first.id, second.id, DispatchContent.REPORT, Medium.LETTER, payload=report)
    assert row is not None and row.intent is MessageIntent.DISPATCH and row.state is DispatchState.UNDER_WAY
    assert row.arrival_epoch is not None and row.arrival_epoch >= ctx.epoch
    tally = DispatchTally()
    await tend_dispatches(context(realm.session, epoch=row.arrival_epoch), tally)
    assert row.state is DispatchState.DELIVERED and tally.delivered == 1
    belief = await realm.session.scalar(select(BeliefRow).where(BeliefRow.holder_node_id == second.id, BeliefRow.subject_node_id == first.id))
    assert belief is not None and belief.attribute == "wealth"


async def test_a_gift_wins_a_favour_and_a_dream_travels_by_dream(realm: Realm) -> None:
    ctx = context(realm.session)
    first = await settlement(realm, "Corrin")
    second = await settlement(realm, "Dunmere")
    row = await send(ctx, first.id, second.id, DispatchContent.GIFT_NOTICE, Medium.MAGIC_SENDING, payload={"commodity": "grain"})
    assert row is not None and row.arrival_epoch == ctx.epoch
    await tend_dispatches(ctx, DispatchTally())
    favour = await realm.session.scalar(select(FavourRow).where(FavourRow.owed_by_node_id == second.id))
    assert favour is not None and favour.origin is FavourOrigin.GIFT and favour.owed_to_node_id == first.id
    vision = MessageRow(epoch=ctx.epoch, sender_node_id=first.id, recipient_node_id=second.id, intent=MessageIntent.DREAM, text="a vision")
    assert vision.medium is Medium.DREAM


async def test_a_spy_network_reads_plain_letters_and_seizes_them_in_war(realm: Realm) -> None:
    ctx = context(realm.session, tuned(communication={"spy_intercept_pct": 100, "forge_replace_pct": 0}))
    sender = await settlement(realm, "Elmstead")
    recipient = await settlement(realm, "Fallow")
    watcher = await settlement(realm, "Greyhold")
    realm.session.add(SpyNetworkRow(owner_entity_id=watcher.id, target_entity_id=sender.id, depth=100, since_epoch=1))
    await realm.session.flush()
    report = {FACTS: {str(sender.id): {"defense": 30}}}
    row = await send(ctx, sender.id, recipient.id, DispatchContent.REPORT, Medium.LETTER, payload=report)
    assert row is not None
    row.arrival_epoch = ctx.epoch + 5
    await tend_dispatches(ctx, DispatchTally())
    assert row.intercepted_by_node_id == watcher.id
    assert await realm.session.scalar(select(BeliefRow).where(BeliefRow.holder_node_id == watcher.id)) is not None


async def test_codebreakers_break_a_cipher_by_the_traffic_they_intercept(realm: Realm) -> None:
    ctx = context(realm.session, tuned(communication={"codebreak_pct": 100}))
    owner = await settlement(realm, "Harrow")
    breaker = await settlement(realm, "Isling")
    cipher = CipherRow(owner_node_id=owner.id, strength=1, broken_by=[], attempts={}, since_epoch=1, locked=[])
    realm.session.add(cipher)
    await realm.session.flush()
    row = await send(ctx, owner.id, breaker.id, DispatchContent.PLEA, Medium.LETTER)
    assert row is not None and row.enciphered
    row.intercepted_by_node_id = breaker.id
    await realm.session.flush()
    tally = CipherTally()
    await attack(ctx, cipher, tally)
    assert breaker.id in cipher.broken_by and tally.broken == 1
    secret = await realm.session.scalar(select(SecretRow).where(SecretRow.holder_node_id == breaker.id, SecretRow.kind == IntrigueSecret.BROKEN_CIPHER))
    assert secret is not None and secret.about_node_id == owner.id


async def test_opinion_drifts_toward_fortune_and_feeds_legitimacy(realm: Realm) -> None:
    ctx = context(realm.session, tuned(communication={"opinion_drift_pct": 100}))
    realm_node = await make(realm.session, "Kingdom of Juniper", EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    town = await settlement(realm, "Juniper", prosperity=90)
    ruler = await mortal(realm, "Kell", location_id=town.id)
    realm.session.add(PolityMemberRow(polity_entity_id=realm_node.id, member_entity_id=town.id))
    realm.session.add(OfficeRow(polity_entity_id=realm_node.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id, powers=[]))
    realm.session.add(OfficeRow(polity_entity_id=realm_node.id, kind=OfficeKind.HERALD, holder_entity_id=ruler.id, powers=[]))
    await realm.session.flush()
    await tend_community(ctx, town, await LawBook.load(realm.session), OpinionTally())
    row = await realm.session.get(PublicOpinionRow, (town.id, ruler.id))
    assert row is not None and row.subject is OpinionSubject.RULER and row.approval > 0
    assert await mean_approval(ctx, [town.id], ruler.id) == row.approval


async def test_zealous_temples_of_a_god_raise_its_approval(realm: Realm) -> None:
    ctx = context(realm.session, tuned(communication={"sermon_approval": 20}))
    god = await son(realm.session, "Ilvar", realm.world.id)
    stranger = await son(realm.session, "Oriel", realm.world.id)
    town = await settlement(realm, "Lanthorn")
    cult = await make(realm.session, "The Lantern Rite", EntityType.CULT, CultStats(followers=40, zeal=50), world_id=realm.world.id, location_id=town.id)
    temple = await make(
        realm.session, "Lantern Hall", EntityType.STRUCTURE, StructureStats(), world_id=realm.world.id, location_id=town.id, engine_kind=EngineKind.TEMPLE
    )
    await link(realm.session, cult.id, god.id, BondKind.WORSHIPS)
    realm.session.add(CultHoldingRow(cult_entity_id=cult.id, holding_entity_id=temple.id, kind=HoldingKind.TEMPLE))
    await realm.session.flush()
    assert await sermons(ctx, town, god.id) == 10
    assert await sermons(ctx, town, stranger.id) == 0


async def test_an_enemy_takes_a_signal_link(realm: Realm) -> None:
    ctx = context(realm.session)
    owner = await settlement(realm, "Kestrel")
    enemy = await settlement(realm, "Lorn")
    link = SignalLinkRow(
        owner_node_id=owner.id,
        kind=SignalKind.BEACON_CHAIN,
        from_region_id=realm.region.id,
        to_region_id=realm.far_region.id,
        state=SignalState.ACTIVE,
        since_epoch=1,
        locked=[],
    )
    realm.session.add(link)
    realm.session.add(OccupationRow(region_entity_id=realm.far_region.id, occupier_entity_id=enemy.id, since_epoch=1))
    await realm.session.flush()
    tally = SignalTally()
    await fall_links(ctx, tally)
    assert link.state in {SignalState.CAPTURED, SignalState.BURNED} and tally.captured + tally.burned == 1
