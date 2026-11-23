from dataclasses import replace

from sqlalchemy import select

from aerona.db.tables.culture import HolderTechniqueRow, RumourRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.db.tables.renown import DeedClaimRow, LoreTradeRow, ReputationRow, RulerCurrencyRow
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.knowledge import KnowledgeKind
from aerona.domain.enums.mind import ActKind, MemoryKind
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.renown import ClaimKind, ClaimStatus, LorePrice, ReputationAxis
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.mortal.profile import ensure_profile
from aerona.engine.phases.renown import fade_and_sum
from aerona.engine.renown.book import acclaim, standing_with
from aerona.engine.renown.claims import punish, tend_claims
from aerona.engine.renown.currencies import CurrencyTally, on_act, restraint, spend_prestige, tend_currencies
from aerona.engine.renown.deeds import DeedTally, axis_for, credit, deed_seen, expose, hearsay, new_claim, record_deed
from aerona.engine.renown.lore import trade, value_of
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, make, mortal, settlement

RULES = Rules()


def tuned(**namespaces: dict[str, int]) -> Rules:
    rules = RULES
    for name, changes in namespaces.items():
        rules = replace(rules, **{name: replace(getattr(rules, name), **changes)})
    return rules


async def test_an_act_is_read_through_each_community_ethics_into_a_reputation(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Ashby")
    actor = await mortal(realm, "Bram", location_id=town.id)
    assert axis_for(ActKind.KILLING_IN_WAR, 60) is ReputationAxis.HEROISM
    assert axis_for(ActKind.KILLING_IN_WAR, -60) is ReputationAxis.CRUELTY
    assert axis_for(ActKind.BUILDING_TEMPLES, 0) is ReputationAxis.PIETY
    deed = await deed_seen(ctx, town.id, actor.id, ActKind.KILLING_IN_WAR, -80)
    assert deed is not None and deed.axis is ReputationAxis.CRUELTY and deed.witnesses == 1
    glory, infamy = await standing_with(realm.session, actor.id, town.id)
    assert infamy > 0 and glory == 0
    claim = await realm.session.scalar(select(DeedClaimRow).where(DeedClaimRow.deed_id == deed.id))
    assert claim is not None and claim.kind is ClaimKind.TRUE and claim.credited > 0


async def test_rumours_carry_a_deed_and_reputations_fade_but_raise_renown(realm: Realm) -> None:
    ctx = context(realm.session, tuned(local_renown={"hearsay_pct": 100, "aggregate_pct": 100}))
    home, far = await settlement(realm, "Cleve"), await settlement(realm, "Dunmore")
    hero = await mortal(realm, "Edric", location_id=home.id)
    deed = await record_deed(ctx, hero.id, ReputationAxis.HEROISM, 40, place_id=home.id)
    assert deed is not None
    incident = IncidentRow(kind="test.deed", epoch=ctx.epoch)
    realm.session.add(incident)
    await realm.session.flush()
    deed.incident_id = incident.id
    realm.session.add(RumourRow(incident_id=incident.id, carrier_entity_id=far.id, source_entity_id=home.id, fidelity=50, hops=1, epoch=ctx.epoch, locked=[]))
    await realm.session.flush()
    tally = DeedTally()
    await hearsay(ctx, tally)
    heard = await realm.session.scalar(select(ReputationRow).where(ReputationRow.subject_node_id == hero.id, ReputationRow.community_node_id == far.id))
    assert tally.heard == 1 and heard is not None and heard.value == 20
    profile, _ = await ensure_profile(realm.session, hero.id, ctx.epoch)
    profile.renown = 0
    later = context(realm.session, ctx.rules, epoch=ctx.epoch + 1)
    await fade_and_sum(later)
    assert heard.value == 20 - RULES.local_renown.fade
    assert profile.renown > 0


async def test_a_false_claim_steals_hearsay_until_it_is_exposed(realm: Realm) -> None:
    ctx = context(realm.session)
    town, far = await settlement(realm, "Fenwick"), await settlement(realm, "Garth")
    doer, liar = await mortal(realm, "Hale", location_id=town.id), await mortal(realm, "Ivo", location_id=town.id)
    deed = await record_deed(ctx, doer.id, ReputationAxis.HEROISM, 50, place_id=town.id)
    assert deed is not None
    claim = new_claim(deed.id, liar.id, ClaimKind.FALSE, ctx.epoch)
    realm.session.add(claim)
    await realm.session.flush()
    await credit(ctx, deed, far.id, 30)
    stolen = await realm.session.scalar(select(ReputationRow).where(ReputationRow.subject_node_id == liar.id, ReputationRow.community_node_id == far.id))
    assert stolen is not None and stolen.value == 30 and claim.credited == 30
    await expose(ctx, deed, claim, DeedTally())
    assert claim.status is ClaimStatus.EXPOSED and stolen.value == 0
    trick = await realm.session.scalar(select(ReputationRow).where(ReputationRow.subject_node_id == liar.id, ReputationRow.axis == ReputationAxis.TRICKERY))
    assert trick is not None and trick.value > 0
    grudge = await realm.session.scalar(select(MemoryRow).where(MemoryRow.holder_node_id == doer.id, MemoryRow.kind == MemoryKind.HUMILIATED_ME))
    assert grudge is not None
    assert await punish(context(realm.session, tuned(claims={"punish_pct": 100})), claim)
    await tend_claims(ctx, DeedTally())


async def test_rulers_gain_dread_and_tyranny_spend_prestige_and_restrain_factions(realm: Realm) -> None:
    ctx = context(realm.session, tuned(currencies={"dread_fade": 0, "tyranny_fade": 0}))
    town = await settlement(realm, "Harrow")
    realm_entity = await make(realm.session, "Kingdom", EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    ruler = await mortal(realm, "Jory", location_id=town.id)
    realm.session.add(PolityMemberRow(polity_entity_id=realm_entity.id, member_entity_id=town.id))
    realm.session.add(OfficeRow(polity_entity_id=realm_entity.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id, powers=[], locked=[]))
    await realm.session.flush()
    await on_act(ctx, ruler.id, ActKind.EXECUTION, -60, town.id)
    purse = await realm.session.get(RulerCurrencyRow, ruler.id)
    assert purse is not None and purse.dread == RULES.currencies.dread_execution and purse.tyranny == RULES.currencies.tyranny_act
    await acclaim(realm.session, ruler.id, town.id, ReputationAxis.HONOUR, amount=80, epoch=ctx.epoch)
    await tend_currencies(ctx, CurrencyTally())
    assert purse.prestige > 0
    purse.prestige = 50
    assert await spend_prestige(ctx, ruler.id) > 1 and purse.prestige == 50 - RULES.currencies.law_cost
    suppress, press = await restraint(ctx, realm_entity.id)
    assert suppress < 1 and press > 1


async def test_lore_is_worth_less_the_more_hold_it_and_trading_pays(realm: Realm) -> None:
    ctx = context(realm.session)
    seller, buyer = await settlement(realm, "Keld"), await settlement(realm, "Lyme")
    realm.session.add(HolderTechniqueRow(holder_entity_id=seller.id, technique=next(iter(Technique)), since_epoch=1, secret=True))
    await realm.session.flush()
    item = (KnowledgeKind.TECHNIQUE, next(iter(Technique)).value, None)
    before = await value_of(ctx, item)
    row = await trade(ctx, seller, buyer, item, value=before)
    assert row is not None and row.price is LorePrice.RENOWN
    assert await value_of(ctx, item) < before
    assert await realm.session.get(HolderTechniqueRow, (buyer.id, next(iter(Technique)))) is not None
    assert await realm.session.scalar(select(LoreTradeRow.id)) is not None
    assert await realm.session.scalar(select(ReputationRow).where(ReputationRow.subject_node_id == seller.id)) is not None
