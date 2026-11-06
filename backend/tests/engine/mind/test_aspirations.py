from dataclasses import replace

from sqlalchemy import select

from aerona.db.tables.body import ConditionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import ModifierRow
from aerona.db.tables.mind import FearRow, InspirationRow, LifeDreamRow, MindRow, PerkRow, SkillRow, ThoughtRow, WantRow
from aerona.domain.enums.body import ConditionKind, HarmCause
from aerona.domain.enums.mind import (
    ActKind,
    DreamState,
    Facet,
    FearKind,
    FocusKind,
    InspirationKind,
    InspirationState,
    LifeGoal,
    MoodState,
    SkillKind,
    SkillSource,
    ThoughtKind,
    ValueAxis,
    ValueHolder,
    WantKind,
)
from aerona.domain.enums.modifier import ModifierSource
from aerona.domain.enums.mortal import LifeStage
from aerona.engine.body.conditions import gain_condition
from aerona.engine.mind.aspirations import (
    AspirationTally,
    aspire,
    fear_near,
    focus_rate,
    gain_conviction,
    grant_perks,
    pursue,
    refresh_wants,
    seed_fears,
    settle_focus,
    steered_values,
)
from aerona.engine.mind.book import ensure_mind_row, stored_values, write_values
from aerona.engine.mind.ethics import shift_conviction
from aerona.engine.mind.inspiration import resolute, tend_inspiration
from aerona.engine.mind.split import write_facets
from aerona.engine.mortal.kinship import marry
from aerona.engine.mortal.profile import ensure_profile
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, mortal, region_record, settlement, store_map

RULES = Rules()


def eager(**changes: int) -> Rules:
    return replace(RULES, aspirations=replace(RULES.aspirations, **changes))


async def thought_kinds(realm: Realm, holder: int) -> list[ThoughtKind]:
    return list(await realm.session.scalars(select(ThoughtRow.kind).where(ThoughtRow.holder_node_id == holder)))


async def adult(realm: Realm, name: str) -> EntityRow:
    hero = await mortal(realm, name)
    profile, _ = await ensure_profile(realm.session, hero.id, 3)
    profile.life_stage = LifeStage.ADULT
    await ensure_mind_row(realm.session, hero, 3)
    return hero


def skill(holder: int, kind: SkillKind, level: int) -> SkillRow:
    return SkillRow(holder_node_id=holder, skill=kind, level=level, peak=level, last_used_epoch=1, source=SkillSource.PLAYER)


async def test_an_adult_takes_up_a_dream_and_milestones_bring_hope_and_conviction(realm: Realm) -> None:
    ctx = context(realm.session, eager(dream_pct=100))
    hero = await adult(realm, "Tamsin")
    tally = AspirationTally()
    await pursue(ctx, hero, tally)
    dream = await realm.session.get(LifeDreamRow, hero.id)
    assert dream is not None and tally.dreams == 1 and dream.state is DreamState.PURSUING
    dream.goal, dream.target_node_id = LifeGoal.MASTER_A_CRAFT, None
    realm.session.add(skill(hero.id, SkillKind.SMITHING, RULES.aspirations.skill_full))
    await realm.session.flush()
    profile, _ = await ensure_profile(realm.session, hero.id, ctx.epoch)
    before = profile.conviction
    await pursue(ctx, hero, tally)
    assert dream.state is DreamState.FULFILLED and dream.milestones == [33, 66, 100]
    assert profile.conviction == before + 3 * RULES.aspirations.conviction_gain
    kinds = await thought_kinds(realm, hero.id)
    assert ThoughtKind.DREAM_PROGRESS in kinds and ThoughtKind.DREAM_FULFILLED in kinds


async def test_a_held_dream_keeps_its_progress(realm: Realm) -> None:
    ctx = context(realm.session)
    hero = await adult(realm, "Orrin")
    realm.session.add(
        LifeDreamRow(
            holder_node_id=hero.id, goal=LifeGoal.MASTER_A_CRAFT, milestones=[], progress=10, state=DreamState.PURSUING, started_epoch=1, locked=["progress"]
        )
    )
    realm.session.add(skill(hero.id, SkillKind.SMITHING, 90))
    await realm.session.flush()
    await pursue(ctx, hero, AspirationTally())
    dream = await realm.session.get_one(LifeDreamRow, hero.id)
    assert dream.progress == 10 and dream.state is DreamState.PURSUING


async def test_a_want_to_marry_is_met_by_a_wedding_and_wants_steer_callings(realm: Realm) -> None:
    ctx = context(realm.session)
    hero = await adult(realm, "Bryn")
    partner = await adult(realm, "Cael")
    realm.session.add(WantRow(holder_node_id=hero.id, kind=WantKind.MARRY, epoch=ctx.epoch, locked=[]))
    await realm.session.flush()
    await marry(realm.session, hero, partner, ctx.epoch)
    tally = AspirationTally()
    await refresh_wants(ctx, hero, tally)
    want = await realm.session.scalar(select(WantRow).where(WantRow.holder_node_id == hero.id, WantRow.kind == WantKind.MARRY))
    assert want is not None and want.fulfilled_epoch == ctx.epoch and tally.wants_met == 1
    assert ThoughtKind.WANT_FULFILLED in await thought_kinds(realm, hero.id)
    pushed = steered_values(RULES, {}, {WantKind.GAIN_WEALTH})
    assert any(value != 0 for value in pushed.values())


async def test_fears_follow_temperament_and_a_heroic_resolve_holds_them_back(realm: Realm) -> None:
    ctx = context(realm.session, eager(inspiration_pct=100))
    hero = await adult(realm, "Wren")
    await write_facets(realm.session, hero.id, {facet: 50 for facet in Facet})
    assert await seed_fears(ctx, hero) > 0
    assert await seed_fears(ctx, hero) == 0
    assert len(list(await realm.session.scalars(select(FearRow).where(FearRow.holder_node_id == hero.id)))) <= RULES.aspirations.fear_count
    realm.session.add(
        InspirationRow(holder_node_id=hero.id, kind=InspirationKind.HEROIC_RESOLVE, started_epoch=1, deadline_epoch=9, state=InspirationState.BURNING)
    )
    await realm.session.flush()
    assert await resolute(realm.session, hero.id)


async def perk_modifiers(realm: Realm, holder: int) -> list[ModifierRow]:
    query = select(ModifierRow).where(ModifierRow.target_node_id == holder, ModifierRow.source_kind == ModifierSource.PERK)
    return list(await realm.session.scalars(query))


async def test_a_focus_grows_skills_faster_and_unlocks_perks_that_leave_with_it(realm: Realm) -> None:
    ctx = context(realm.session)
    hero = await adult(realm, "Idris")
    realm.session.add(skill(hero.id, SkillKind.SMITHING, 70))
    await realm.session.flush()
    assert await settle_focus(ctx, hero) is FocusKind.CRAFT
    assert await focus_rate(realm.session, RULES, hero.id, SkillKind.SMITHING) > 1
    assert await grant_perks(ctx, hero, FocusKind.CRAFT) > 0
    modifiers = list(
        await realm.session.scalars(select(ModifierRow).where(ModifierRow.target_node_id == hero.id, ModifierRow.source_kind == ModifierSource.PERK))
    )
    assert modifiers
    await grant_perks(ctx, hero, FocusKind.MARTIAL)
    assert not list(
        await realm.session.scalars(select(PerkRow).where(PerkRow.holder_node_id == hero.id, PerkRow.perk.in_([m.reason_key[5:] for m in modifiers])))
    )


async def test_an_elated_mortal_is_seized_and_an_unspent_fever_leaves_visions(realm: Realm) -> None:
    ctx = context(realm.session, eager(inspiration_pct=100))
    hero = await adult(realm, "Sorrel")
    realm.session.add(skill(hero.id, SkillKind.SMITHING, 70))
    profile, _ = await ensure_profile(realm.session, hero.id, ctx.epoch)
    profile.mood = MoodState.ELATED
    await realm.session.flush()
    assert await tend_inspiration(ctx, hero) is not None
    row = await realm.session.scalar(select(InspirationRow).where(InspirationRow.holder_node_id == hero.id))
    assert row is not None and ThoughtKind.INSPIRED in await thought_kinds(realm, hero.id)
    if row.state is InspirationState.BURNING and row.kind is not InspirationKind.HEROIC_RESOLVE:
        later = context(realm.session, ctx.rules, epoch=row.deadline_epoch)
        assert await tend_inspiration(later, hero) == "failed"
        assert await realm.session.scalar(select(ConditionRow).where(ConditionRow.bearer_node_id == hero.id, ConditionRow.kind == ConditionKind.VISIONS))


async def test_conviction_grows_breaks_and_overturns_a_belief_unless_held(realm: Realm) -> None:
    ctx = context(realm.session)
    hero = await adult(realm, "Mabon")
    await write_values(realm.session, ValueHolder.PERSONAL, hero.id, {ValueAxis.MERCY: 60})
    profile, _ = await ensure_profile(realm.session, hero.id, ctx.epoch)
    profile.conviction = 15
    await shift_conviction(ctx, hero.id, -RULES.aspirations.conviction_loss, ActKind.TORTURE)
    assert profile.conviction == 50 and ThoughtKind.DISILLUSIONED in await thought_kinds(realm, hero.id)
    assert (await stored_values(realm.session, ValueHolder.PERSONAL, hero.id))[ValueAxis.MERCY] != 60
    profile.locked = ["conviction"]
    await gain_conviction(realm.session, RULES, hero.id, 30, ctx.epoch)
    assert profile.conviction == 50


async def test_a_held_mind_keeps_its_aspirations(realm: Realm) -> None:
    ctx = context(realm.session, eager(dream_pct=100))
    hero = await adult(realm, "Elowen")
    mind = await realm.session.get_one(MindRow, hero.id)
    mind.locked = ["aspirations"]
    await aspire(ctx, hero, AspirationTally(), resolved=False)
    assert await realm.session.get(LifeDreamRow, hero.id) is None


async def test_a_want_to_travel_sets_out_for_a_neighbour_and_is_met_there(realm: Realm) -> None:
    ctx = context(realm.session, eager(want_travel_pct=100))
    await store_map(
        realm.session,
        realm.world.id,
        [region_record(realm.region.id, neighbours=[realm.far_region.id]), region_record(realm.far_region.id, neighbours=[realm.region.id])],
    )
    home = await settlement(realm, "Hearth", location_id=realm.region.id)
    away = await settlement(realm, "Yonder", location_id=realm.far_region.id)
    hero = await adult(realm, "Rhosyn")
    hero.location_id = home.id
    realm.session.add(WantRow(holder_node_id=hero.id, kind=WantKind.TRAVEL, epoch=ctx.epoch, locked=[]))
    await realm.session.flush()
    tally = AspirationTally()
    await aspire(ctx, hero, tally, resolved=False)
    assert tally.journeys == 1 and hero.location_id == away.id
    await refresh_wants(ctx, hero, tally)
    want = await realm.session.scalar(select(WantRow).where(WantRow.holder_node_id == hero.id, WantRow.kind == WantKind.TRAVEL))
    assert want is not None and want.fulfilled_epoch == ctx.epoch


async def test_a_fear_of_the_dark_comes_near_the_sightless(realm: Realm) -> None:
    ctx = context(realm.session)
    hero = await adult(realm, "Neve")
    assert not await fear_near(ctx, hero, FearKind.DARK)
    await gain_condition(ctx, hero, ConditionKind.AGE_BLINDNESS, HarmCause.AGE, severity=2)
    assert await fear_near(ctx, hero, FearKind.DARK)
