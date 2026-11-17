from dataclasses import replace

from sqlalchemy import select

from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.mind import CultureEthicRow, CultureHonourRow, PreferenceRow, ThoughtRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import TraditionFunction
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import ActKind, EthicalStance, HonourModel, PreferenceKind, ThoughtKind, ValueAxis, ValueHolder
from aerona.domain.enums.mortal import DeathCause
from aerona.domain.models.entity_stats import SpeciesStats
from aerona.engine.mind.book import ensure_mind_row, write_values
from aerona.engine.mind.ethics import conscience, drift_ethics, ethic_reading, killing_act, restore, seed_ethics, seed_honour, spread_shame
from aerona.engine.mind.preferences import adopt_totem, demand_factor, make_taboos, material_factor, prefs_of, seed_culture, seed_mortal, write_pref
from aerona.engine.mind.thoughts import think
from aerona.engine.mortal.kinship import marry
from aerona.engine.mortal.profile import ensure_profile
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, link, make, mortal, people

RULES = Rules()


async def test_a_people_gains_tastes_and_its_mortals_inherit_some(realm: Realm) -> None:
    ctx = context(realm.session)
    folk = await people(realm, "Ashen")
    await ensure_mind_row(realm.session, folk, ctx.epoch)
    await write_values(realm.session, ValueHolder.CULTURE, folk.id, {ValueAxis.WEALTH: 80})
    assert await seed_culture(ctx, folk) > 0
    tastes = await prefs_of(realm.session, folk.id)
    assert any(value > 0 for value in tastes.values()) and any(value < 0 for value in tastes.values())
    child = await mortal(realm, "Ivra")
    await link(realm.session, child.id, folk.id, BondKind.MEMBER_OF)
    await seed_mortal(ctx, child)
    assert set(await prefs_of(realm.session, child.id)) <= set(tastes)


async def test_tastes_move_demand_and_premiums_and_disgust_becomes_a_taboo(realm: Realm) -> None:
    ctx = context(realm.session)
    folk = await people(realm, "Velt")
    loved = {(PreferenceKind.FOOD, "fish"): 80, (PreferenceKind.MATERIAL, "amber"): 80}
    assert demand_factor(RULES, loved, "fish") > 1 > demand_factor(RULES, {(PreferenceKind.FOOD, "fish"): -80}, "fish")
    assert material_factor(RULES, loved, "amber") > 1
    await write_pref(realm.session, folk.id, PreferenceKind.FOOD, "livestock", -90)
    assert await make_taboos(ctx, folk) == 1
    taboo = await realm.session.scalar(select(TraditionProfileRow).where(TraditionProfileRow.kind == TraditionFunction.TABOO))
    assert taboo is not None and taboo.taboo_target == "livestock"
    assert await make_taboos(ctx, folk) == 0


async def test_a_beloved_creature_becomes_a_totem(realm: Realm) -> None:
    ctx = context(realm.session)
    folk = await people(realm, "Orm")
    stag = await make(realm.session, "Silver Stag", EntityType.SPECIES, SpeciesStats(), world_id=realm.world.id)
    await write_pref(realm.session, folk.id, PreferenceKind.CREATURE, str(stag.id), 90, target_node_id=stag.id)
    assert await adopt_totem(ctx, folk)
    assert not await adopt_totem(ctx, folk)


async def test_ethics_follow_beliefs_witnesses_judge_by_them_and_holds_keep_them(realm: Realm) -> None:
    rules = replace(RULES, ethics=replace(RULES.ethics, drift_epochs=1))
    ctx = context(realm.session, rules)
    folk = await people(realm, "Harl")
    await ensure_mind_row(realm.session, folk, ctx.epoch)
    await write_values(
        realm.session, ValueHolder.CULTURE, folk.id, {ValueAxis.MERCY: 100, ValueAxis.MARTIAL: -100, ValueAxis.HIERARCHY: -100, ValueAxis.LAW: 100}
    )
    assert await seed_ethics(ctx, folk) == len(ActKind)
    torture = await realm.session.get(CultureEthicRow, (folk.id, ActKind.TORTURE))
    assert torture is not None and torture.stance is EthicalStance.UNTHINKABLE
    assert await ethic_reading(realm.session, rules, folk.id, ActKind.TORTURE, {}) == -85
    await write_values(realm.session, ValueHolder.CULTURE, folk.id, {ValueAxis.MERCY: -100})
    theft = await realm.session.get(CultureEthicRow, (folk.id, ActKind.THEFT))
    assert theft is not None
    theft.locked = ["stance"]
    before = theft.stance
    assert await drift_ethics(ctx, folk) > 0
    assert torture.stance is EthicalStance.SHAMEFUL and theft.stance is before


async def test_killings_are_named_and_guilt_follows_what_ones_people_abhor(realm: Realm) -> None:
    ctx = context(realm.session)
    folk = await people(realm, "Dun")
    await ensure_mind_row(realm.session, folk, ctx.epoch)
    await write_values(realm.session, ValueHolder.CULTURE, folk.id, {ValueAxis.FAMILY: 100, ValueAxis.KINSHIP: 100})
    await seed_ethics(ctx, folk)
    first = await mortal(realm, "Brann")
    second = await mortal(realm, "Cael")
    await link(realm.session, first.id, folk.id, BondKind.MEMBER_OF)
    await link(realm.session, first.id, second.id, BondKind.PARENT_OF)
    assert await killing_act(realm.session, second, first.id, DeathCause.MURDER) is ActKind.KILLING_KIN
    assert await killing_act(realm.session, second, None, DeathCause.DESPAIR) is ActKind.SUICIDE
    assert await killing_act(realm.session, second, first.id, DeathCause.BATTLE) is ActKind.KILLING_KIN
    stance = await conscience(ctx, first.id, ActKind.KILLING_KIN, second.id)
    assert stance in {EthicalStance.SHAMEFUL, EthicalStance.UNTHINKABLE}
    guilt = await realm.session.scalar(select(ThoughtRow).where(ThoughtRow.holder_node_id == first.id, ThoughtRow.kind == ThoughtKind.ACTED_AGAINST_CONSCIENCE))
    profile = await realm.session.get(MortalProfileRow, first.id)
    assert guilt is not None and profile is not None and profile.infamy > 0


async def test_in_an_honour_culture_shame_spreads_to_kin_and_is_restored(realm: Realm) -> None:
    rules = replace(RULES, ethics=replace(RULES.ethics, restoration_pct=100))
    ctx = context(realm.session, rules)
    folk = await people(realm, "Kor")
    await ensure_mind_row(realm.session, folk, ctx.epoch)
    await write_values(realm.session, ValueHolder.CULTURE, folk.id, {ValueAxis.HONOUR: 90})
    assert await seed_honour(ctx, folk)
    honour = await realm.session.get(CultureHonourRow, folk.id)
    assert honour is not None and honour.model is HonourModel.HONOUR
    shamed = await mortal(realm, "Ama")
    kin = await mortal(realm, "Ebb")
    rival = await mortal(realm, "Tor")
    for one in (shamed, kin):
        await link(realm.session, one.id, folk.id, BondKind.MEMBER_OF)
    await marry(realm.session, shamed, kin, ctx.epoch)
    await think(realm.session, rules, shamed.id, ThoughtKind.WAS_SHAMED, ctx.epoch, subject_id=rival.id)
    assert await spread_shame(ctx, shamed) >= 1
    await ensure_profile(realm.session, rival.id, ctx.epoch)
    assert await restore(ctx, kin) == 1
    relief = await realm.session.scalar(select(ThoughtRow).where(ThoughtRow.holder_node_id == kin.id, ThoughtRow.kind == ThoughtKind.SHAME_RESTORED))
    assert relief is not None
    assert await realm.session.scalar(select(PreferenceRow.id).limit(1)) is None
