from sqlalchemy import select

from aerona.db.tables.intrigue import BeliefRow, FavourRow, HookRow, IdentityRow, SchemeRow, SecretRow, TrueNameRow
from aerona.db.tables.mind import FacetRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.intrigue import (
    BeliefSource,
    FavourOrigin,
    HookDemand,
    HookSource,
    HookStrength,
    IdentityReason,
    IntrigueSecret,
    PlotKind,
    SchemePhase,
    TrueNameCause,
)
from aerona.domain.enums.mind import Facet
from aerona.engine.intrigue.beliefs import BeliefView, believe, fade_beliefs
from aerona.engine.intrigue.favours import call_favour
from aerona.engine.intrigue.identities import assume, tend_identity
from aerona.engine.intrigue.leverage import press
from aerona.engine.intrigue.names import name_bearer, name_power, rename, teach_name
from aerona.engine.intrigue.schemes import SchemeTally, begin_scheme, tend_scheme
from aerona.engine.intrigue.secrets import expose, grant_hook, keep_secret, learn
from aerona.engine.intrigue.sources import hidden_birth
from aerona.engine.intrigue.talk import gift_earns, gossip_secret
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.naming import Namer
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, link, mortal, settlement, tuned

RULES = Rules()


async def test_a_learned_secret_gives_a_hook_and_exposure_shames_its_keeper(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Saltmere")
    keeper = await mortal(realm, "Ilse", location_id=town.id)
    snoop = await mortal(realm, "Tam", location_id=town.id)
    secret = await keep_secret(ctx, keeper.id, IntrigueSecret.MURDER)
    assert secret is not None and secret.known_by == [keeper.id] and secret.severity == 85
    assert await learn(ctx, secret, snoop.id)
    hook = await realm.session.scalar(select(HookRow).where(HookRow.holder_node_id == snoop.id))
    assert hook is not None and hook.strength is HookStrength.STRONG and hook.secret_id == secret.id
    assert await expose(ctx, secret, by_id=snoop.id)
    assert secret.exposed_epoch == ctx.epoch
    assert await realm.session.scalar(select(HookRow).where(HookRow.secret_id == secret.id)) is None
    assert not await expose(ctx, secret)


async def test_gossip_spreads_secrets_and_gifts_leave_favours(realm: Realm) -> None:
    ctx = context(realm.session, tuned(intrigue={"gossip_pct": 100}))
    town = await settlement(realm, "Brindle")
    keeper = await mortal(realm, "Ana", location_id=town.id)
    gossip = await mortal(realm, "Bex", location_id=town.id)
    listener = await mortal(realm, "Cy", location_id=town.id)
    secret = await keep_secret(ctx, keeper.id, IntrigueSecret.AFFAIR, known_by=(gossip.id,))
    assert secret is not None
    assert await gossip_secret(ctx, gossip.id, listener.id)
    assert listener.id in secret.known_by
    belief = await realm.session.scalar(select(BeliefRow).where(BeliefRow.holder_node_id == listener.id))
    assert belief is not None and belief.source is BeliefSource.RUMOUR
    await gift_earns(ctx, gossip.id, listener.id)
    favour = await realm.session.scalar(select(FavourRow).where(FavourRow.owed_by_node_id == listener.id))
    assert favour is not None and favour.origin is FavourOrigin.GIFT and favour.owed_to_node_id == gossip.id
    assert await call_favour(ctx, favour, honour=True)
    assert favour.honoured is True and favour.called_epoch == ctx.epoch


async def test_a_hook_presses_a_target_into_a_marriage(realm: Realm) -> None:
    ctx = context(realm.session, tuned(intrigue={"hook_comply_pct": 100}))
    town = await settlement(realm, "Fennick")
    suitor = await mortal(realm, "Orla", location_id=town.id)
    target = await mortal(realm, "Pim", location_id=town.id)
    hook = await grant_hook(ctx, suitor.id, target.id, HookSource.SECRET, strong=False)
    assert hook is not None
    done = await press(ctx, suitor.id, target.id, HookDemand.MARRIAGE)
    assert done is not None and "wed" in done
    assert hook.used_epoch == ctx.epoch
    assert await press(ctx, suitor.id, target.id, HookDemand.MARRIAGE) is None


async def test_a_false_identity_wears_thin_and_falls(realm: Realm) -> None:
    ctx = context(realm.session, tuned(intrigue={"identity_slip": 60, "identity_look": 50}))
    town = await settlement(realm, "Gorse")
    spy = await mortal(realm, "Quill", location_id=town.id)
    row = await assume(ctx, spy, IdentityReason.SPY, "Rennet", cover_role="merchant", community_id=town.id)
    assert row is not None
    mask = await realm.session.scalar(select(SecretRow).where(SecretRow.holder_node_id == spy.id, SecretRow.kind == IntrigueSecret.FALSE_IDENTITY))
    assert mask is not None
    realm.session.add(FacetRow(node_id=spy.id, facet=Facet.CAUTION, value=-50))
    row.exposure = 99
    assert await tend_identity(ctx, row)
    assert row.exposed_epoch == ctx.epoch and mask.exposed_epoch == ctx.epoch
    assert await assume(ctx, spy, IdentityReason.EXILE, "Other") is None


async def test_a_scheme_recruits_prepares_and_strikes(realm: Realm) -> None:
    rules = tuned(intrigue={"recruit_epochs": 0, "discovery_pct": 0, "owner_power": 100})
    ctx = context(realm.session, rules)
    town = await settlement(realm, "Hollin")
    plotter = await mortal(realm, "Sela", location_id=town.id)
    rival = await mortal(realm, "Tor", location_id=town.id)
    scheme = await begin_scheme(ctx, plotter, PlotKind.FABRICATE_HOOK, rival)
    assert scheme is not None and scheme.phase is SchemePhase.RECRUIT
    atlas = await RegionAtlas.load(realm.session)
    tally = SchemeTally()
    await tend_scheme(ctx, scheme, tally, atlas)
    assert scheme.phase is SchemePhase.PREPARE
    await tend_scheme(context(realm.session, rules, epoch=4), scheme, tally, atlas)
    assert scheme.power >= 1 and scheme.progress > 0
    scheme.power, scheme.phase = 10000, SchemePhase.EXECUTE
    await tend_scheme(context(realm.session, rules, epoch=5), scheme, tally, atlas)
    assert scheme.phase is SchemePhase.SUCCEEDED and tally.succeeded == 1
    assert await realm.session.scalar(select(HookRow).where(HookRow.holder_node_id == plotter.id, HookRow.target_node_id == rival.id)) is not None
    held_secret = await realm.session.scalar(select(SecretRow).where(SecretRow.holder_node_id == rival.id, SecretRow.kind == IntrigueSecret.CRIME))
    assert held_secret is not None and plotter.id in held_secret.known_by


async def test_true_names_bind_and_are_renewed(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Ivel")
    mage = await mortal(realm, "Uma", location_id=town.id)
    bearer = await mortal(realm, "Vor", location_id=town.id)
    row = await name_bearer(ctx, bearer.id, "Esk-Vorrath")
    assert row is not None and row.known_by == [bearer.id]
    assert await name_power(ctx, mage.id, bearer) == 1.0
    assert await teach_name(ctx, row, mage.id)
    assert await name_power(ctx, mage.id, bearer) > 1.0
    assert await realm.session.scalar(select(HookRow).where(HookRow.holder_node_id == mage.id, HookRow.source == HookSource.TRUE_NAME)) is not None
    assert await rename(ctx, Namer(realm.session, RULES), row, cause=TrueNameCause.INITIATION, name="Esk-Ithel")
    assert row.name == "Esk-Ithel" and row.known_by == [bearer.id]
    assert await realm.session.scalar(select(HookRow).where(HookRow.holder_node_id == mage.id, HookRow.source == HookSource.TRUE_NAME)) is None
    assert await realm.session.get(TrueNameRow, bearer.id) is row


async def test_beliefs_stray_from_the_truth_fade_and_fall_back_to_a_guess(realm: Realm) -> None:
    ctx = context(realm.session, tuned(belief_state={"decay": 50}))
    first = await settlement(realm, "Juniper")
    second = await settlement(realm, "Kestrel", prosperity=80)
    view = BeliefView(realm.session, ctx.rules, first.id)
    assert await view.of(second.id, "wealth", 70) == 70
    planted = await believe(ctx, first.id, second.id, "wealth", 5, source=BeliefSource.DECEPTION, confidence=60, false=True)
    assert planted is not None and planted.value == 5 and planted.false
    assert await view.of(second.id, "wealth", 70) == 5
    later = context(realm.session, ctx.rules, epoch=ctx.epoch + 1)
    assert await fade_beliefs(later) == 1
    assert planted.confidence == 10
    await fade_beliefs(context(realm.session, ctx.rules, epoch=ctx.epoch + 2))
    await realm.session.flush()
    assert await realm.session.get(BeliefRow, planted.id) is None


async def test_a_child_of_an_affair_carries_a_hidden_parentage(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Larch")
    wife = await mortal(realm, "Mira", location_id=town.id)
    husband = await mortal(realm, "Ned", location_id=town.id)
    lover = await mortal(realm, "Oto", location_id=town.id)
    child = await mortal(realm, "Pell", location_id=town.id, age=1)
    await link(realm.session, wife.id, husband.id, BondKind.SPOUSE_OF)
    await hidden_birth(ctx, wife, lover, [child])
    kept = await realm.session.scalar(select(SecretRow).where(SecretRow.holder_node_id == wife.id, SecretRow.kind == IntrigueSecret.ILLEGITIMATE_CHILD))
    parentage = await realm.session.scalar(select(SecretRow).where(SecretRow.holder_node_id == child.id, SecretRow.kind == IntrigueSecret.TRUE_PARENTAGE))
    assert kept is not None and kept.about_node_id == child.id
    assert parentage is not None and parentage.about_node_id == lover.id and set(parentage.known_by) >= {wife.id, lover.id}
    assert await realm.session.scalar(select(IdentityRow)) is None
    assert await realm.session.scalar(select(SchemeRow)) is None
