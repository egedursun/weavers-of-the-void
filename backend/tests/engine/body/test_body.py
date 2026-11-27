from typing import cast

import pytest
from sqlalchemy import select

from aerona.catalog.anatomy import FINGERS, Part, anatomy_of
from aerona.core.random import SeededRandom
from aerona.db.tables.body import BodyRow, ConditionRow, InjuryRow, MaimedCohortRow, ProsthesisRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.body import (
    BodyBuild,
    BodyPlan,
    BodyReading,
    ConditionKind,
    DamageType,
    HarmCause,
    HeightClass,
    InjuryKind,
    InjuryState,
    MaimedKind,
    MedicineTier,
    StrikeStyle,
)
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.calendar import epoch_start_year
from aerona.domain.models.entity_stats import KnowledgeStats
from aerona.engine.body import healing
from aerona.engine.body.book import bedridden, effective, ensure_body, frame_style, legacy_plan_from_words, size_of
from aerona.engine.body.cohorts import return_maimed, tend_cohorts, war_appetite
from aerona.engine.body.customs import ensure_customs
from aerona.engine.body.describe import body_lines
from aerona.engine.body.healing import fit_prosthesis, heal_wounds, mend
from aerona.engine.body.hits import Harm, harm_resisted, kind_for, loss_for
from aerona.engine.body.marks import leaves_mark
from aerona.engine.body.state import refresh
from aerona.engine.lifecycle.wounds import WoundOutcome, apply_hits
from aerona.engine.phases.body import body_conditions, body_society, body_survey, seek_reader
from aerona.engine.phases.mortals import mortal_wounds
from aerona.engine.polity.offices import whole
from aerona.engine.primitives.queries import active_bonds, add_flag
from aerona.engine.primitives.stats import stat
from aerona.engine.records import death_path
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, link, make, mortal, people, settlement, son, tuned

RULES = Rules()
HUMAN = anatomy_of(BodyPlan.HUMANOID)


def part(key: str) -> Part:
    found = HUMAN.part(key)
    assert found is not None
    return found


def test_the_kind_table_follows_the_damage_type() -> None:
    table = RULES.injury
    assert kind_for(table, DamageType.CUT, part("right_hand"), 5, HarmCause.BATTLE) is InjuryKind.SEVERED
    assert kind_for(table, DamageType.CUT, part("right_hand"), 3, HarmCause.BATTLE) is InjuryKind.DEEP_CUT
    assert kind_for(table, DamageType.CUT, part("torso"), 5, HarmCause.BATTLE) is InjuryKind.DEEP_CUT
    assert kind_for(table, DamageType.PIERCE, part("left_eye"), 3, HarmCause.BATTLE) is InjuryKind.GOUGED
    assert kind_for(table, DamageType.PIERCE, part("heart"), 5, HarmCause.BATTLE) is InjuryKind.DESTROYED
    assert kind_for(table, DamageType.PIERCE, part("gut"), 2, HarmCause.MONSTER) is InjuryKind.BITE
    assert kind_for(table, DamageType.BLUNT, part("head"), 4, HarmCause.BATTLE) is InjuryKind.CRUSH
    assert kind_for(table, DamageType.VOID, part("torso"), 1, HarmCause.CURSE) is InjuryKind.VOID_TOUCH
    assert kind_for(table, DamageType.HOLY, part("face"), 2, HarmCause.GOD) is InjuryKind.DIVINE_BRAND
    assert loss_for(table, InjuryKind.SEVERED, 5) == 100
    assert loss_for(table, InjuryKind.DIVINE_BRAND, 3) == 0
    assert harm_resisted(anatomy_of(BodyPlan.INCORPOREAL), DamageType.CUT)
    assert not harm_resisted(anatomy_of(BodyPlan.INCORPOREAL), DamageType.HOLY)


async def test_a_severed_sword_hand_collapses_melee_but_not_scholarship(realm: Realm) -> None:
    king = await mortal(realm, "Aldric", role=MortalRole.RULER)
    ctx = context(realm.session)
    await refresh(realm.session, RULES, king, ctx.epoch)
    healthy = await effective(realm.session, king, "strength")
    wounding = await apply_hits(ctx, king, Harm(25, HarmCause.DUEL, "fell in a duel", part="right_hand", kind=InjuryKind.SEVERED, severity=5), lethal=False)
    assert wounding.outcome is WoundOutcome.WOUNDED and wounding.injuries[0].kind is InjuryKind.SEVERED
    body = await realm.session.get(BodyRow, king.id)
    assert body is not None and body.melee < 100 and body.scholarship == 100
    assert await effective(realm.session, king, "strength") < healthy
    assert (stat(king, "hp") or 0) >= 1


async def test_a_ruinous_blow_to_the_heart_kills(realm: Realm) -> None:
    victim = await mortal(realm, "Bera")
    ctx = context(realm.session)
    wounding = await apply_hits(ctx, victim, Harm(10, HarmCause.BATTLE, "fell in battle", part="heart", kind=InjuryKind.DESTROYED, severity=5))
    assert wounding.outcome is WoundOutcome.DIED
    assert victim.status is not EntityStatus.CANON
    assert any(row.state is InjuryState.LETHAL for row in wounding.injuries)


async def test_mortal_wounds_heal_into_scars_and_health_returns(realm: Realm) -> None:
    hunter = await mortal(realm, "Cael", hp=100)
    rules = tuned(healing={"heal_severity_2": 100, "infection_cut": 0, "infection_other": 0, "infection_deep_cut": 0})
    ctx = context(realm.session, rules)
    await apply_hits(ctx, hunter, Harm(20, HarmCause.QUEST, "fell", part="left_arm", kind=InjuryKind.CUT, severity=2), lethal=False)
    before = stat(hunter, "hp") or 0
    await heal_wounds(context(realm.session, rules, epoch=4))
    rows = list(await realm.session.scalars(select(InjuryRow).where(InjuryRow.bearer_node_id == hunter.id)))
    assert rows and all(row.state in {InjuryState.HEALED_SCAR, InjuryState.PERMANENT} for row in rows)
    assert (stat(hunter, "hp") or 0) > before


async def test_surgery_takes_a_festering_limb_instead_of_a_life(realm: Realm) -> None:
    town = await settlement(realm, "Harrow")
    soldier = await mortal(realm, "Dovan", location_id=town.id, role=MortalRole.WARRIOR)
    lore = await knowledge_at(realm, KnowledgeBranch.MEDICINE, level=2)
    await link(realm.session, town.id, lore.id, BondKind.KNOWS)
    rules = tuned(healing={"lethal_after_years": 50, "amputation_chance": 100}, conditions={})
    ctx = context(realm.session, rules)
    wounding = await apply_hits(ctx, soldier, Harm(20, HarmCause.BATTLE, "fell", part="left_leg", kind=InjuryKind.DEEP_CUT, severity=3), lethal=False)
    wounding.injuries[0].state = InjuryState.INFECTED
    await heal_wounds(context(realm.session, rules, epoch=4))
    row = wounding.injuries[0]
    assert soldier.status is EntityStatus.CANON
    assert row.kind is InjuryKind.SEVERED and row.function_loss == 100


async def knowledge_at(realm: Realm, branch: KnowledgeBranch, *, level: int) -> EntityRow:
    stats = KnowledgeStats(level=level, spread=20)
    return await make(realm.session, f"{branch.value} lore", EntityType.KNOWLEDGE, stats, world_id=realm.world.id, knowledge_branch=branch)


async def test_a_prosthesis_gives_back_part_of_the_lost_function(realm: Realm) -> None:
    captain = await mortal(realm, "Eira", role=MortalRole.CAPTAIN)
    ctx = context(realm.session)
    wounding = await apply_hits(ctx, captain, Harm(25, HarmCause.BATTLE, "fell", part="left_leg", kind=InjuryKind.SEVERED, severity=5), lethal=False)
    row = wounding.injuries[0]
    row.state = InjuryState.PERMANENT
    await refresh(realm.session, RULES, captain, ctx.epoch)
    lame = (await realm.session.get(BodyRow, captain.id)).mobility
    await fit_prosthesis(ctx, captain, row, part("left_leg"), MaterialKind.STAR_METAL, maker=None, quality=100)
    await refresh(realm.session, RULES, captain, ctx.epoch)
    body = await realm.session.get(BodyRow, captain.id)
    assert body.mobility > lame
    fitted = list(await realm.session.scalars(select(ProsthesisRow).where(ProsthesisRow.bearer_node_id == captain.id)))
    assert fitted and fitted[0].item_entity_id is not None


async def test_a_blind_scholar_reads_through_an_apprentice(realm: Realm) -> None:
    sage = await mortal(realm, "Faro", role=MortalRole.SAGE)
    ctx = context(realm.session)
    for eye in ("left_eye", "right_eye"):
        await apply_hits(ctx, sage, Harm(15, HarmCause.TORTURE, "fell", part=eye, kind=InjuryKind.GOUGED, severity=4), lethal=False)
    blind = (await realm.session.get(BodyRow, sage.id)).scholarship
    pupil = await mortal(realm, "Gil", role=MortalRole.APPRENTICE)
    await link(realm.session, pupil.id, sage.id, BondKind.APPRENTICE_OF)
    await refresh(realm.session, RULES, sage, ctx.epoch)
    assert (await realm.session.get(BodyRow, sage.id)).scholarship > blind


async def test_a_purity_people_sets_aside_its_maimed_ruler(realm: Realm) -> None:
    folk = await people(realm, "The Pale")
    patron = await son(realm.session, "Lumen", realm.world.id)
    patron.domain_primary, patron.domain_secondary = Domain.LIGHT, Domain.SUN
    await link(realm.session, folk.id, patron.id, BondKind.WORSHIPS)
    ruler = await mortal(realm, "Hald", role=MortalRole.RULER)
    await link(realm.session, ruler.id, folk.id, BondKind.MEMBER_OF)
    await link(realm.session, ruler.id, folk.id, BondKind.RULES)
    custom = await ensure_customs(realm.session, RULES, folk)
    assert custom.reading is BodyReading.PURITY and custom.wholeness_required
    ctx = context(realm.session)
    wounding = await apply_hits(ctx, ruler, Harm(25, HarmCause.DUEL, "fell", part="right_hand", kind=InjuryKind.SEVERED, severity=5), lethal=False)
    wounding.injuries[0].state = InjuryState.PERMANENT
    await refresh(realm.session, RULES, ruler, ctx.epoch)
    assert (await realm.session.get(BodyRow, ruler.id)).presence < 100
    await body_society(ctx)
    rulers = [bond.source_node_id for bond in await active_bonds(realm.session, [BondKind.RULES], targets=[folk.id])]
    assert rulers and ruler.id not in rulers


async def test_maimed_veterans_come_home_and_weigh_on_their_people(realm: Realm) -> None:
    town = await settlement(realm, "Kest", population=1000, prosperity=60)
    ctx = context(realm.session)
    placed = await return_maimed(ctx, town, 200)
    rows = list(await realm.session.scalars(select(MaimedCohortRow).where(MaimedCohortRow.community_entity_id == town.id)))
    assert placed == sum(row.count for row in rows) > 0
    assert any(row.kind is MaimedKind.ONE_EYED for row in rows)
    assert await war_appetite(ctx, town) < 1
    await tend_cohorts(ctx)
    assert (stat(town, "prosperity") or 0) < 60
    assert sum(row.count for row in rows) < placed


async def test_madness_follows_low_sanity_and_the_chosen_bear_their_mark(realm: Realm) -> None:
    seer = await mortal(realm, "Iona", role=MortalRole.SEER)
    seer.sanity = 5
    chosen = await mortal(realm, "Jory", role=MortalRole.CHOSEN)
    await add_flag(realm.session, chosen.id, EntityFlag.CHOSEN, 1)
    rules = tuned(conditions={"madness_chance": 100})
    await body_conditions(context(realm.session, rules))
    kinds = {row.kind for row in await realm.session.scalars(select(ConditionRow).where(ConditionRow.ended_epoch.is_(None)))}
    assert ConditionKind.CHOSEN_MARK in kinds
    assert kinds & {ConditionKind.PARANOIA, ConditionKind.VISIONS, ConditionKind.RAGE, ConditionKind.MELANCHOLY}


async def test_survey_gives_bodies_and_fatal_wounds_to_the_fallen(realm: Realm) -> None:
    living = await mortal(realm, "Kai")
    fallen = await mortal(realm, "Lorn")
    fallen.status, fallen.end_epoch = EntityStatus.DEAD, 2
    await add_flag(realm.session, fallen.id, EntityFlag.FELL_IN_BATTLE, 1)
    god = await son(realm.session, "Vael", realm.world.id)
    await body_survey(context(realm.session))
    assert await realm.session.get(BodyRow, living.id) is not None
    divine = await realm.session.get(BodyRow, god.id)
    assert divine is not None and divine.plan is BodyPlan.DIVINE_MANIFEST
    wounds = list(await realm.session.scalars(select(InjuryRow).where(InjuryRow.bearer_node_id == fallen.id)))
    assert len(wounds) == 1 and wounds[0].state is InjuryState.LETHAL


async def test_gods_take_divine_wounds_and_a_miracle_mends(realm: Realm) -> None:
    god = await son(realm.session, "Morn", realm.world.id)
    ctx = context(realm.session)
    wounding = await apply_hits(ctx, god, Harm(30, HarmCause.GOD, "was struck down", source_node_id=None))
    assert wounding.injuries and god.hp < 100
    mortal_row = await mortal(realm, "Nessa")
    await apply_hits(ctx, mortal_row, Harm(20, HarmCause.BATTLE, "fell", part=FINGERS, kind=InjuryKind.SEVERED, severity=3), lethal=False)
    body = await ensure_body(realm.session, RULES, mortal_row, ctx.epoch)
    assert body.fingers < 10
    assert await mend(ctx, mortal_row, lasting=True) >= 1
    assert body.fingers == 10
    assert (await realm.session.get(BodyRow, mortal_row.id)).craft == 100


async def test_every_violent_death_leaves_its_wound(realm: Realm) -> None:
    ctx = context(realm.session)
    captor = await people(realm, "Hill Folk")
    executed = await mortal(realm, "Arn")
    assert await death_path(ctx, executed, "executed by the Hill Folk", captor.id, "execution", forced=True, harm=HarmCause.PUNISHMENT)
    faded = await mortal(realm, "Bera", hp=0)
    await mortal_wounds(ctx)
    for victim, cause in ((executed, HarmCause.PUNISHMENT), (faded, HarmCause.ACCIDENT)):
        wounds = list(await realm.session.scalars(select(InjuryRow).where(InjuryRow.bearer_node_id == victim.id)))
        assert victim.status is EntityStatus.DEAD
        assert [(row.state, row.cause_kind) for row in wounds] == [(InjuryState.LETHAL, cause)]


async def test_the_touch_of_the_void_lowers_sanity_for_good(realm: Realm) -> None:
    ctx = context(realm.session)
    seer = await mortal(realm, "Ysolde")
    seer.sanity = 90
    await apply_hits(ctx, seer, Harm(30, HarmCause.CURSE, "touched by the void", damage_type=DamageType.VOID), lethal=False)
    wounds = list(await realm.session.scalars(select(InjuryRow).where(InjuryRow.bearer_node_id == seer.id, InjuryRow.kind == InjuryKind.VOID_TOUCH)))
    assert wounds
    ceiling = 100 - sum(row.severity for row in wounds) * ctx.rules.injury.void_sanity_per_severity
    assert seer.sanity == max(0, ceiling) < 90
    seer.sanity = 100
    await refresh(realm.session, ctx.rules, seer, ctx.epoch)
    assert seer.sanity == max(0, ceiling)


async def test_species_bodies_follow_their_nature_and_size_shapes_the_blow(realm: Realm) -> None:
    assert legacy_plan_from_words("A coiling sea serpent of the reefs") is BodyPlan.SERPENTINE
    assert legacy_plan_from_words("Clockwork golems that guard the vaults") is BodyPlan.CONSTRUCT
    assert legacy_plan_from_words("pale wraiths of the moor") is BodyPlan.INCORPOREAL
    rules = Rules()
    giant = BodyRow(node_id=1, plan=BodyPlan.HUMANOID, traits=[], fingers=10, height_class=HeightClass.GIANT, build=BodyBuild.GIANT, locked=[])
    child = BodyRow(node_id=2, plan=BodyPlan.HUMANOID, traits=[], fingers=10, height_class=HeightClass.SHORT, build=BodyBuild.SLIGHT, locked=[])
    assert frame_style(rules, size_of(giant), child) is StrikeStyle.TRAMPLE
    assert frame_style(rules, size_of(child), giant) is StrikeStyle.LOW
    assert frame_style(rules, size_of(child), child) is StrikeStyle.NORMAL


async def test_survey_gives_the_slain_a_wound_from_their_killer(realm: Realm) -> None:
    killer = await mortal(realm, "Dask")
    victim = await mortal(realm, "Ivo")
    victim.status, victim.end_epoch = EntityStatus.DEAD, 2
    await link(realm.session, killer.id, victim.id, BondKind.KILLED)
    await body_survey(context(realm.session))
    wounds = list(await realm.session.scalars(select(InjuryRow).where(InjuryRow.bearer_node_id == victim.id)))
    assert [(row.state, row.cause_kind, row.cause_node_id) for row in wounds] == [(InjuryState.LETHAL, HarmCause.DUEL, killer.id)]


async def test_the_bedridden_cannot_fight_and_a_blinded_sage_finds_a_reader(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Inkhold")
    sage = await mortal(realm, "Old Teo", location_id=town.id, role=MortalRole.SAGE, age=70)
    pupil = await mortal(realm, "Mira", location_id=town.id, age=15, intellect=80)
    body = await ensure_body(realm.session, ctx.rules, sage, ctx.epoch)
    body.scholarship = 10
    assert await seek_reader(ctx, sage) is pupil
    assert await seek_reader(ctx, sage) is None
    sick = await mortal(realm, "Hal", hp=10)
    await refresh(realm.session, ctx.rules, sick, ctx.epoch)
    sick_body = await ensure_body(realm.session, ctx.rules, sick, ctx.epoch)
    assert bedridden(ctx.rules, sick) and sick_body.melee == 0 and sick_body.command == 0


class CountingRandom:
    def __init__(self) -> None:
        self.rolls = 0

    def chance(self, _percent: float) -> bool:
        self.rolls += 1
        return False


async def test_a_wound_taken_on_campaign_faces_the_camp_for_every_season_of_its_year(realm: Realm, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(healing, "infection_chance", lambda *_args: 1.0)
    ctx = context(realm.session)
    care = healing.Care(tier=MedicineTier.NONE, healer=None, disease=50, metallurgy=0, artisan=None)
    rolls = []
    for campaign in (False, True):
        rng = CountingRandom()
        row = InjuryRow(state=InjuryState.FRESH)
        assert not healing.infected(
            ctx,
            row,
            BodyRow(),
            care,
            skill=0,
            ward=1.0,
            rng=cast(SeededRandom, rng),
            campaign=campaign,
        )
        rolls.append(rng.rolls)
    assert rolls == [1, 1 + ctx.rules.campaigns.seasons_per_war_epoch]


async def test_a_healed_bruise_leaves_no_mark_and_never_counts_a_ruler_as_maimed(realm: Realm) -> None:
    ruler = await mortal(realm, "Ysolde", hp=100)
    rules = tuned(healing={"heal_severity_3": 100, "infection_other": 0, "permanent_severity_3_pct": 0})
    ctx = context(realm.session, rules)
    await apply_hits(ctx, ruler, Harm(20, HarmCause.ACCIDENT, "fell", part="left_arm", kind=InjuryKind.BRUISE, severity=3), lethal=False)
    await heal_wounds(context(realm.session, rules, epoch=4))
    bruise = await realm.session.scalar(select(InjuryRow).where(InjuryRow.bearer_node_id == ruler.id))
    assert bruise is not None and bruise.state is InjuryState.HEALED_SCAR and not bruise.visible and bruise.function_loss == 0
    assert not leaves_mark(bruise) and await whole(ctx, ruler)
    assert not any("bruise" in line for line in await body_lines(realm.session, rules, ruler, private=True))
    bruise.kind, bruise.visible = InjuryKind.CUT, True
    await realm.session.flush()
    assert leaves_mark(bruise) and not await whole(ctx, ruler)


async def test_an_injury_is_dated_by_the_world_year_not_the_year_inside_the_age(realm: Realm) -> None:
    hunter = await mortal(realm, "Dated Cael", hp=100)
    ctx = context(realm.session, epoch=4)
    await apply_hits(ctx, hunter, Harm(5, HarmCause.QUEST, "fell", part="left_arm", kind=InjuryKind.CUT, severity=1), lethal=False)
    years = set(await realm.session.scalars(select(InjuryRow.year).where(InjuryRow.bearer_node_id == hunter.id)))
    start = epoch_start_year(4, ctx.rules.time.years_per_epoch)
    assert years and all(year is not None and start <= year < start + ctx.rules.time.years_per_epoch for year in years)
