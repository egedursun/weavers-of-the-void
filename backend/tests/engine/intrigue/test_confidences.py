from sqlalchemy import select

from aerona.db.tables.intrigue import HookRow
from aerona.db.tables.relations import RelationshipRow
from aerona.domain.enums.intrigue import FavourOrigin, IntrigueSecret
from aerona.engine.intrigue.favours import owe
from aerona.engine.intrigue.secrets import keep_secret
from aerona.engine.intrigue.talk import ask_back, confide_own
from aerona.engine.mortal.profile import ensure_profile
from aerona.engine.relations.book import relation
from tests.engine.society.factories import Realm, context, mortal, tuned

OPEN = tuned(intrigue={"confide_pct": 100})


async def test_a_confidant_learns_a_secret_once_and_gains_a_hook(realm: Realm) -> None:
    ctx = context(realm.session, OPEN)
    teller, listener, lover = await mortal(realm, "Teller"), await mortal(realm, "Listener"), await mortal(realm, "Lover")
    secret = await keep_secret(ctx, teller.id, IntrigueSecret.AFFAIR, about_id=lover.id, known_by=(lover.id,), source="affair")
    assert secret is not None
    assert await confide_own(ctx, teller.id, listener.id)
    assert listener.id in secret.known_by
    hook = await realm.session.scalar(select(HookRow).where(HookRow.holder_node_id == listener.id, HookRow.target_node_id == teller.id))
    assert hook is not None
    assert not await confide_own(ctx, teller.id, listener.id)


async def test_an_exposed_secret_or_a_guarded_tongue_tells_nothing(realm: Realm) -> None:
    teller, listener, lover = await mortal(realm, "Teller"), await mortal(realm, "Listener"), await mortal(realm, "Lover")
    secret = await keep_secret(context(realm.session, OPEN), teller.id, IntrigueSecret.AFFAIR, about_id=lover.id, known_by=(lover.id,))
    assert secret is not None
    assert not await confide_own(context(realm.session, tuned(intrigue={"confide_pct": 0})), teller.id, listener.id)
    secret.exposed_epoch = 2
    assert not await confide_own(context(realm.session, OPEN), teller.id, listener.id)
    assert listener.id not in secret.known_by


async def test_asking_back_a_favour_needs_one_owed(realm: Realm) -> None:
    asker, giver = await mortal(realm, "Asker"), await mortal(realm, "Giver")
    assert await ask_back(context(realm.session), asker.id, giver.id) is None


async def test_a_friend_honours_a_favour_asked_back_and_trust_grows(realm: Realm) -> None:
    ctx = context(realm.session)
    asker, giver = await mortal(realm, "Asker"), await mortal(realm, "Giver")
    realm.session.add(RelationshipRow(holder_node_id=giver.id, subject_node_id=asker.id, friendship=30, kinds=[], since_epoch=1, last_epoch=1, locked=[]))
    favour = await owe(ctx, giver.id, asker.id, FavourOrigin.GIFT, 20)
    assert favour is not None
    assert await ask_back(ctx, asker.id, giver.id) is True
    assert favour.called_epoch == ctx.epoch and favour.honoured
    view = await relation(realm.session, asker.id, giver.id)
    assert view is not None and view.friendship > 0


async def test_a_cold_debtor_refuses_and_loses_honour(realm: Realm) -> None:
    ctx = context(realm.session)
    asker, giver = await mortal(realm, "Asker"), await mortal(realm, "Giver")
    realm.session.add(RelationshipRow(holder_node_id=giver.id, subject_node_id=asker.id, friendship=-30, kinds=[], since_epoch=1, last_epoch=1, locked=[]))
    favour = await owe(ctx, giver.id, asker.id, FavourOrigin.GIFT, 20)
    assert favour is not None
    standing, _ = await ensure_profile(realm.session, giver.id, ctx.epoch)
    before = standing.honour
    assert await ask_back(ctx, asker.id, giver.id) is False
    assert favour.honoured is False
    assert standing.honour == max(0, before - ctx.rules.intrigue.favour_refusal)
    assert await ask_back(ctx, asker.id, giver.id) is None
