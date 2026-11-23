from sqlalchemy import select

from aerona.catalog.kinds.harm import HARM_DEATHS
from aerona.core.random import SeededRandom
from aerona.db.tables.body import BodyRow, InjuryRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MarriageRow, MortalProfileRow
from aerona.domain.enums.body import BodyFunction, BodyPart, DamageType, HarmCause, InjuryKind, InjuryState
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.demography import SexKind
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.mortal import CrimeKind, DeathCause, HarshnessScale, LifeStage, MarriageEnd, PunishmentKind, StressBreak
from aerona.domain.models.entity_stats import MortalStats
from aerona.engine.body.book import function_level
from aerona.engine.body.hits import Harm, venom_mix
from aerona.engine.body.state import refresh, sanity_ceiling
from aerona.engine.lifecycle.mortal_death import die
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mortal.acts import break_weights, stress_break
from aerona.engine.mortal.course import live_one_epoch, seed_mortal, upkeep_standing
from aerona.engine.mortal.death import manner_of
from aerona.engine.mortal.justice import sentence
from aerona.engine.mortal.kin import children_of, close_kin_of, parents_of, siblings_of, spouses_of
from aerona.engine.mortal.kinship import add_parent, backfill_kin, end_marriage, marry
from aerona.engine.mortal.life import fertility_level, hazard_chance, inherited_summaries, stage_bounds, stage_for
from aerona.engine.mortal.profile import ensure_profile
from aerona.engine.phases.births import deliver
from aerona.engine.primitives.harshness import harshness
from aerona.engine.primitives.naming import Namer
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, link, mortal, tuned

RULES = Rules()


def test_the_harshness_dial_scales_every_rate_as_a_group() -> None:
    heroic = tuned(harshness={"profile": 0})
    brutal = tuned(harshness={"profile": 2})
    for scale in HarshnessScale:
        if scale is HarshnessScale.NOTABLE_SURVIVAL:
            assert harshness(heroic, scale) > harshness(RULES, scale) > harshness(brutal, scale)
        else:
            assert harshness(heroic, scale) < harshness(RULES, scale) < harshness(brutal, scale)


def test_life_stages_follow_the_lifespan_curve() -> None:
    bounds = stage_bounds(RULES, None, 80)
    assert stage_for(bounds, 1) is LifeStage.INFANT
    assert stage_for(bounds, 8) is LifeStage.CHILD
    assert stage_for(bounds, 18) is LifeStage.YOUTH
    assert stage_for(bounds, 40) is LifeStage.ADULT
    assert stage_for(bounds, 62) is LifeStage.ELDER
    assert stage_for(bounds, 90) is LifeStage.ANCIENT


def test_fertility_has_a_window_by_sex() -> None:
    assert fertility_level(RULES, None, SexKind.BEARER, age=30, lifespan=80, body=None) == 100
    assert fertility_level(RULES, None, SexKind.BEARER, age=55, lifespan=80, body=None) == 0
    assert fertility_level(RULES, None, SexKind.BEGETTER, age=55, lifespan=80, body=None) == 100
    assert fertility_level(RULES, None, SexKind.BEGETTER, age=5, lifespan=80, body=None) == 0


def test_old_age_kills_by_a_hazard_curve() -> None:
    young = hazard_chance(RULES, 40, 80, 100, medicine=False)
    at_cap = hazard_chance(RULES, 80, 80, 100, medicine=False)
    past = hazard_chance(RULES, 96, 80, 100, medicine=False)
    assert young == 0
    assert 0 < at_cap < past
    assert hazard_chance(RULES, 80, 80, 20, medicine=False) > at_cap
    assert hazard_chance(RULES, 80, 80, 100, medicine=True) < at_cap


def test_harm_maps_to_a_typed_manner_of_death() -> None:
    assert manner_of(HarmCause.PUNISHMENT) is DeathCause.EXECUTION
    assert manner_of(None) is DeathCause.UNKNOWN
    assert set(HARM_DEATHS) == set(HarmCause)


def test_venom_follows_the_attackers_gland() -> None:
    mix = {DamageType.CUT: 50, DamageType.VENOM: 10}
    assert DamageType.VENOM not in venom_mix(mix, 0)
    assert venom_mix(mix, 100)[DamageType.VENOM] == 10
    assert venom_mix(mix, None) == mix


def test_a_crushed_head_lowers_the_most_sanity_one_can_hold() -> None:
    assert sanity_ceiling(RULES, [], 100) == 100
    assert sanity_ceiling(RULES, [], 40) < 100


async def test_a_hearing_wound_dulls_the_hearing_function(realm: Realm) -> None:
    scout = await mortal(realm, "Ivo")
    ctx = context(realm.session)
    await apply_hits(ctx, scout, Harm(20, HarmCause.DUEL, "fell", part=BodyPart.LEFT_EAR, kind=InjuryKind.SEVERED, severity=5), lethal=False)
    await apply_hits(ctx, scout, Harm(20, HarmCause.DUEL, "fell", part=BodyPart.RIGHT_EAR, kind=InjuryKind.SEVERED, severity=5), lethal=False)
    body = await realm.session.get(BodyRow, scout.id)
    assert body is not None and body.hearing < 100
    assert await function_level(realm.session, RULES, scout.id, BodyFunction.HEARING) < 100


async def test_seeding_gives_body_and_mind_sex_and_a_stage(realm: Realm) -> None:
    elder = await mortal(realm, "Orun", age=70, lifespan=80)
    ctx = context(realm.session)
    await seed_mortal(ctx, elder)
    profile = await realm.session.get(MortalProfileRow, elder.id)
    assert profile is not None and profile.life_stage is LifeStage.ELDER
    assert stat(elder, "endurance") is not None and stat(elder, "wisdom") is not None
    assert elder.social_class is not None


async def test_elders_decline_and_grow_wise(realm: Realm) -> None:
    elder = await mortal(realm, "Pell", age=70, lifespan=80, strength=60)
    ctx = context(realm.session)
    await seed_mortal(ctx, elder)
    before = (stat(elder, "strength") or 0, stat(elder, "wisdom") or 0)
    await live_one_epoch(ctx, elder)
    assert (stat(elder, "strength") or 0) < before[0]
    assert (stat(elder, "wisdom") or 0) > before[1]


async def test_typed_kin_is_read_both_ways(realm: Realm) -> None:
    mother = await mortal(realm, "Ama")
    father = await mortal(realm, "Bren")
    first = await mortal(realm, "Cyr")
    second = await mortal(realm, "Dov")
    for child in (first, second):
        await add_parent(realm.session, mother.id, child.id, 1)
        await add_parent(realm.session, father.id, child.id, 1)
    await marry(realm.session, mother, father, 1)
    assert set(await parents_of(realm.session, first.id)) == {mother.id, father.id}
    assert set(await children_of(realm.session, mother.id)) == {first.id, second.id}
    assert await siblings_of(realm.session, first.id) == [second.id]
    assert await spouses_of(realm.session, mother.id) == [father.id]
    assert {mother.id, father.id, second.id} <= set(await close_kin_of(realm.session, first.id))


async def test_old_descent_and_love_become_typed_kin_once(realm: Realm) -> None:
    mother = await mortal(realm, "Eda")
    father = await mortal(realm, "Fen")
    child = await mortal(realm, "Gal")
    await link(realm.session, child.id, mother.id, BondKind.DESCENDS_FROM)
    await link(realm.session, child.id, father.id, BondKind.DESCENDS_FROM)
    await link(realm.session, mother.id, father.id, BondKind.LOVES)
    result = await backfill_kin(realm.session, 3)
    assert result == {"parents": 2, "marriages": 1}
    assert set(await parents_of(realm.session, child.id)) == {mother.id, father.id}
    assert await spouses_of(realm.session, mother.id) == [father.id]
    assert await backfill_kin(realm.session, 3) == {}


async def test_death_widows_and_records_the_manner(realm: Realm) -> None:
    wife = await mortal(realm, "Hala")
    husband = await mortal(realm, "Ivar")
    row = await marry(realm.session, wife, husband, 1)
    ctx = context(realm.session)
    await die(ctx, husband, cause="fell in battle", manner=DeathCause.BATTLE, forced=True)
    profile = await realm.session.get(MortalProfileRow, husband.id)
    assert profile is not None and profile.cause_of_death is DeathCause.BATTLE
    assert row.end_epoch is not None and row.cause_end is MarriageEnd.DEATH
    assert await spouses_of(realm.session, wife.id) == []


async def test_a_divorce_ends_the_spouse_bond(realm: Realm) -> None:
    first = await mortal(realm, "Jora")
    second = await mortal(realm, "Kel")
    row = await marry(realm.session, first, second, 1)
    await end_marriage(realm.session, row, 2, MarriageEnd.DIVORCE)
    assert await spouses_of(realm.session, first.id) == []
    marriages = list(await realm.session.scalars(select(MarriageRow)))
    assert marriages[0].cause_end is MarriageEnd.DIVORCE


async def test_the_law_takes_a_thiefs_hand(realm: Realm) -> None:
    thief = await mortal(realm, "Lun", role=MortalRole.BANDIT)
    judge = await mortal(realm, "Mara", role=MortalRole.RULER)
    ctx = context(realm.session)
    await sentence(ctx, thief, CrimeKind.THEFT, PunishmentKind.HAND, judge=judge)
    rows = list(await realm.session.scalars(select(InjuryRow).where(InjuryRow.bearer_node_id == thief.id)))
    assert any(row.part is BodyPart.RIGHT_HAND and row.kind is InjuryKind.SEVERED for row in rows)
    judge_profile = await realm.session.get(MortalProfileRow, judge.id)
    assert judge_profile is not None and judge_profile.infamy > 0


async def test_treason_can_be_death(realm: Realm) -> None:
    traitor = await mortal(realm, "Nim")
    ctx = context(realm.session)
    await sentence(ctx, traitor, CrimeKind.TREASON, PunishmentKind.DEATH)
    assert traitor.status is not EntityStatus.CANON
    profile = await realm.session.get(MortalProfileRow, traitor.id)
    assert profile is not None and profile.cause_of_death is DeathCause.EXECUTION


async def test_a_mind_past_its_threshold_breaks_and_eases(realm: Realm) -> None:
    sufferer = await mortal(realm, "Oda")
    ctx = context(realm.session)
    profile, _ = await ensure_profile(realm.session, sufferer.id, ctx.epoch)
    profile.stress = 95
    broke = await stress_break(ctx, sufferer, profile)
    assert broke is not None
    assert profile.stress < 95 and profile.last_break is broke


def test_low_loyalty_makes_flight_likelier() -> None:
    loyal = MortalProfileRow(entity_id=1, loyalty_liege=100, locked=[])
    restless = MortalProfileRow(entity_id=2, loyalty_liege=0, locked=[])
    assert break_weights(100, set(), restless)[StressBreak.FLIGHT] > break_weights(100, set(), loyal)[StressBreak.FLIGHT]


async def test_renown_fades_and_legitimacy_follows_office(realm: Realm) -> None:
    lord = await mortal(realm, "Pol", role=MortalRole.RULER)
    ctx = context(realm.session)
    profile, _ = await ensure_profile(realm.session, lord.id, ctx.epoch)
    profile.renown = 80
    await upkeep_standing(ctx, lord, profile)
    assert profile.renown < 80
    assert profile.legitimacy is not None


async def test_childbirth_can_bring_twins(realm: Realm) -> None:
    mother = await mortal(realm, "Qira", age=25, lifespan=80)
    father = await mortal(realm, "Rhun", age=25, lifespan=80)
    rules = tuned(fertility={"twins_pct": 100.0, "stillbirth_pct": 0.0, "mortality_base_pct": 0.0})
    ctx = context(realm.session, rules)
    born = await deliver(ctx, mother, father, Namer(realm.session, rules))
    assert len(born) == rules.fertility.twin_cap
    for child in born:
        assert set(await parents_of(realm.session, child.id)) == {mother.id, father.id}
    assert all(stat(child, "endurance") is not None for child in born)


def test_children_inherit_body_and_mind_near_their_parents_mean() -> None:
    first = EntityRow(id=1, entity_type=EntityType.MORTAL, stats=MortalStats(endurance=80, wisdom=20))
    second = EntityRow(id=2, entity_type=EntityType.MORTAL, stats=MortalStats(endurance=60, wisdom=40))
    values = inherited_summaries(RULES, first, second, SeededRandom.for_epoch(1, 1, "test"))
    assert abs(values["endurance"] - 70) <= RULES.fertility.ability_deviation
    assert abs(values["wisdom"] - 30) <= RULES.fertility.ability_deviation


async def test_lasting_injuries_survive_a_bond_close(realm: Realm) -> None:
    bearer = await mortal(realm, "Sel")
    ctx = context(realm.session)
    await refresh(realm.session, RULES, bearer, ctx.epoch)
    await apply_hits(ctx, bearer, Harm(20, HarmCause.EXPOSURE, "froze", damage_type=DamageType.COLD, severity=2), lethal=False)
    rows = list(await realm.session.scalars(select(InjuryRow).where(InjuryRow.bearer_node_id == bearer.id)))
    assert rows and all(row.cause_kind is HarmCause.EXPOSURE and row.state is not InjuryState.LETHAL for row in rows)
