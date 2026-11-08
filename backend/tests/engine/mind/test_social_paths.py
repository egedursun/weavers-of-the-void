from sqlalchemy import select

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.mind import ThoughtRow
from aerona.db.tables.relations import RelationshipRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import ThoughtKind
from aerona.domain.enums.relations import ContestKind, ContestStake, InteractionKind
from aerona.domain.enums.war import CaptiveStatus
from aerona.domain.models.entity_stats import CultStats
from aerona.engine.mortal.kinship import marry
from aerona.engine.mortal.profile import ensure_profile
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.stats import stat
from aerona.engine.relations.book import ensure_relation
from aerona.engine.relations.contests import STAKES, Bout, best_kind
from aerona.engine.relations.interactions import EFFECTS, load_scene
from tests.engine.society.factories import Realm, context, make, mortal, settlement, son, tuned

K = InteractionKind


async def test_a_spurned_proposal_breaks_a_heart_and_a_wed_lover_strays(realm: Realm) -> None:
    ctx = context(realm.session, tuned(social={"proposal_accept_pct": 100}))
    town = await settlement(realm, "Hollin")
    first = await mortal(realm, "Sela", location_id=town.id)
    second = await mortal(realm, "Tor", location_id=town.id)
    spouse = await mortal(realm, "Mira", location_id=town.id)
    scene = await load_scene(ctx, town.id, [first, second, spouse])
    await EFFECTS[K.PROPOSE](scene, first.id, second.id)
    hurt = await realm.session.scalar(select(ThoughtRow).where(ThoughtRow.holder_node_id == first.id, ThoughtRow.kind == ThoughtKind.HEARTBROKEN))
    assert hurt is not None
    back = await ensure_relation(realm.session, second.id, first.id, ctx.epoch)
    assert back is not None
    back.romance = 100
    await EFFECTS[K.PROPOSE](scene, first.id, second.id)
    betrothed = await realm.session.scalar(select(BondRow).where(BondRow.kind == BondKind.BETROTHED_TO))
    assert betrothed is not None
    await EFFECTS[K.SEDUCE](scene, first.id, spouse.id)
    assert await realm.session.scalar(select(RelationshipRow).where(RelationshipRow.affair.is_(True))) is None
    await marry(realm.session, second, spouse, ctx.epoch)
    married = await load_scene(ctx, town.id, [first, second, spouse])
    await EFFECTS[K.SEDUCE](married, first.id, spouse.id)
    assert await realm.session.scalar(select(RelationshipRow).where(RelationshipRow.affair.is_(True))) is not None


async def test_a_favour_asked_with_nothing_owed_is_refused_and_a_secret_can_be_confided(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Hollin")
    asker, giver = await mortal(realm, "Sela", location_id=town.id), await mortal(realm, "Tor", location_id=town.id)
    scene = await load_scene(ctx, town.id, [asker, giver])
    await EFFECTS[K.ASK_FAVOUR](scene, asker.id, giver.id)
    await EFFECTS[K.CONFIDE_SECRET](scene, asker.id, giver.id)
    assert scene.mortals[asker.id] is asker


async def test_contest_stakes_move_wealth_free_captives_and_swell_a_gods_cult(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Hollin")
    winner, loser = await mortal(realm, "Sela", location_id=town.id), await mortal(realm, "Tor", location_id=town.id)
    assert await best_kind(ctx, winner, loser) in set(ContestKind)
    won, _ = await ensure_profile(realm.session, winner.id, ctx.epoch)
    lost, _ = await ensure_profile(realm.session, loser.id, ctx.epoch)
    won.wealth, lost.wealth = 10, 30
    kind = next(iter(ContestKind))
    await STAKES[ContestStake.WAGER](ctx, Bout(kind, ContestStake.WAGER, winner, loser, wager=20), winner, loser)
    assert (won.wealth, lost.wealth) == (30, 10)
    realm.session.add(CaptiveRow(captive_entity_id=winner.id, captor_entity_id=town.id, status=CaptiveStatus.HELD, taken_epoch=1, locked=[]))
    await realm.session.flush()
    await STAKES[ContestStake.CAPTIVE](ctx, Bout(kind, ContestStake.CAPTIVE, loser, winner), winner, loser)
    held = await realm.session.scalar(select(CaptiveRow).where(CaptiveRow.captive_entity_id == winner.id))
    assert held is not None and held.status is CaptiveStatus.HELD
    await STAKES[ContestStake.CAPTIVE](ctx, Bout(kind, ContestStake.CAPTIVE, winner, loser), winner, loser)
    assert held.status is CaptiveStatus.RELEASED
    await STAKES[ContestStake.DIVINE_FAVOUR](ctx, Bout(kind, ContestStake.DIVINE_FAVOUR, winner, loser), winner, loser)
    god = await son(realm.session, "Vael", realm.world.id)
    cult = await make(realm.session, "The Choir", EntityType.CULT, CultStats(followers=100), world_id=realm.world.id)
    await connect(realm.session, winner.id, god.id, BondKind.WORSHIPS, 1)
    await connect(realm.session, cult.id, god.id, BondKind.WORSHIPS, 1)
    await STAKES[ContestStake.DIVINE_FAVOUR](ctx, Bout(kind, ContestStake.DIVINE_FAVOUR, winner, loser), winner, loser)
    assert (stat(cult, "followers") or 0) > 100
