from pathlib import Path

from sqlalchemy import select

from aerona.db.tables.mind import MindRow
from aerona.db.tables.society import CommunityRelationRow
from aerona.db.tables.warfare import HeroQuestRow
from aerona.domain.enums.body import HarmCause, InjuryKind, InjuryState
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.mind import (
    ActKind,
    MemoryKind,
    NeedKind,
    PressureKind,
    SkillKind,
    SkillSource,
    TraitEffect,
    TraitKind,
    TraitSource,
    ValueAxis,
    ValueHolder,
)
from aerona.domain.enums.society import Commodity
from aerona.domain.enums.war import HeroQuestKind
from aerona.domain.models.entity_stats import FactionStats
from aerona.engine.body.book import effective
from aerona.engine.body.healing import heal_wounds
from aerona.engine.body.hits import Harm
from aerona.engine.body.state import refresh
from aerona.engine.lifecycle.mortal_death import die
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mind.book import (
    add_trait,
    ensure_mind_row,
    needs_of,
    pressures_of,
    set_skill,
    skills_of,
    stored_values,
    traits_of,
    values_for,
    write_pressures,
    write_values,
)
from aerona.engine.mind.depth import read_depth
from aerona.engine.mind.describe import mind_lines
from aerona.engine.mind.drives import closeness, war_drive
from aerona.engine.mind.memories import forget_faded, memories_about, remember
from aerona.engine.mind.opinion import opinion
from aerona.engine.mind.skills import left_to_beg, practise, weather_skills
from aerona.engine.mind.space import value_distance, value_reading
from aerona.engine.phases.mind import famine_aid, mind_memories, mind_needs, mind_opinion, mind_skills, mind_survey, mind_values
from aerona.engine.primitives.society import set_stock, stock
from aerona.engine.services.community_relations import change_relation, refresh_relation, relation
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, link, make, mortal, people, settlement, son, tuned

RULES = Rules()


async def test_value_space_measures_distance_and_reads_acts() -> None:
    gentle = {ValueAxis.MERCY: 80, ValueAxis.MARTIAL: -60}
    harsh = {ValueAxis.MERCY: -80, ValueAxis.MARTIAL: 70}
    assert value_distance(gentle, gentle) == 0
    assert value_distance(gentle, harsh) > value_distance(gentle, {ValueAxis.MERCY: 50})
    assert value_reading(gentle, ActKind.EXECUTION) < 0 < value_reading(harsh, ActKind.EXECUTION)
    assert value_reading(gentle, ActKind.MERCY_TO_ENEMY) > 0


async def test_the_survey_gives_every_holder_a_mind(realm: Realm) -> None:
    folk = await people(realm, "Salt Folk", population=8000)
    god = await son(realm.session, "Vael", realm.world.id)
    await link(realm.session, folk.id, god.id, BondKind.WORSHIPS)
    smith = await mortal(realm, "Orla", role=MortalRole.ARTISAN)
    await link(realm.session, smith.id, folk.id, BondKind.LIVES_IN)
    rival = await people(realm, "Ash Folk", population=4000)
    await link(realm.session, folk.id, rival.id, BondKind.ENEMY)
    await mind_survey(context(realm.session))
    culture = await stored_values(realm.session, ValueHolder.CULTURE, folk.id)
    assert culture[ValueAxis.XENOPHILIA] > 0 and culture[ValueAxis.PURITY] > 0
    assert await stored_values(realm.session, ValueHolder.PERSONAL, smith.id)
    assert await stored_values(realm.session, ValueHolder.DIVINE, god.id)
    traits = await traits_of(realm.session, smith.id)
    assert RULES.traits.birth_min <= len(traits) <= RULES.traits.max_traits
    skills = await skills_of(realm.session, smith.id)
    assert SkillKind.SMITHING in skills and skills[SkillKind.SMITHING].level > 0
    fought = await memories_about(realm.session, folk.id, rival.id)
    assert fought and fought[0].kind is MemoryKind.FOUGHT_US
    assert await realm.session.get(MindRow, god.id) is not None


async def test_a_brave_and_trained_fighter_strikes_harder(realm: Realm) -> None:
    raw = await mortal(realm, "Pell", role=MortalRole.WARRIOR, strength=60)
    veteran = await mortal(realm, "Dunn", role=MortalRole.WARRIOR, strength=60)
    for fighter in (raw, veteran):
        await ensure_mind_row(realm.session, fighter, 3)
    await add_trait(realm.session, veteran.id, TraitKind.BRAVE, TraitSource.PLAYER, 3)
    await set_skill(realm.session, veteran.id, SkillKind.SPEAR, 80, epoch=3, source=SkillSource.PLAYER)
    plain = await effective(realm.session, raw, "strength", rules=RULES)
    seasoned = await effective(realm.session, veteran, "strength", rules=RULES)
    assert seasoned > plain


async def test_practice_raises_a_skill_and_disuse_rusts_it(realm: Realm) -> None:
    smith = await mortal(realm, "Brann", role=MortalRole.ARTISAN)
    await ensure_mind_row(realm.session, smith, 1)
    gained = await practise(realm.session, RULES, smith.id, SkillKind.SMITHING, 500, epoch=1)
    row = (await skills_of(realm.session, smith.id))[SkillKind.SMITHING]
    assert gained > 0 and row.level == gained and row.peak == row.level
    peak = row.level
    await weather_skills(context(realm.session, epoch=1 + RULES.skills.rust_epochs), smith)
    assert row.level < peak
    assert row.level >= round(peak * RULES.skills.rust_floor_pct / 100)


async def test_a_master_teaches_an_apprentice_who_remembers_them(realm: Realm) -> None:
    master = await mortal(realm, "Sela", role=MortalRole.HEALER)
    student = await mortal(realm, "Tam", role=MortalRole.APPRENTICE, age=14)
    for node in (master, student):
        await ensure_mind_row(realm.session, node, 3)
    await set_skill(realm.session, master.id, SkillKind.MEDICINE, 70, epoch=3, source=SkillSource.PLAYER)
    await link(realm.session, student.id, master.id, BondKind.APPRENTICE_OF)
    await mind_skills(context(realm.session, tuned(skills={"teach_xp": 400})))
    assert (await skills_of(realm.session, student.id))[SkillKind.MEDICINE].level > 0
    taught = await memories_about(realm.session, student.id, master.id)
    assert taught and taught[0].kind is MemoryKind.TAUGHT_ME and taught[0].magnitude > 0


async def test_a_wound_that_ends_a_calling_changes_the_role(realm: Realm) -> None:
    soldier = await mortal(realm, "Kel", role=MortalRole.WARRIOR)
    await ensure_mind_row(realm.session, soldier, 3)
    for skill in (SkillKind.SPEAR, SkillKind.SHIELD, SkillKind.BLADE):
        await set_skill(realm.session, soldier.id, skill, 60, epoch=3, source=SkillSource.PLAYER)
    await set_skill(realm.session, soldier.id, SkillKind.TACTICS, 45, epoch=3, source=SkillSource.PLAYER)
    ctx = context(realm.session)
    for arm in ("right_arm", "left_arm"):
        wounding = await apply_hits(ctx, soldier, Harm(15, HarmCause.BATTLE, "fell", part=arm, kind=InjuryKind.SEVERED, severity=5), lethal=False)
        for row in wounding.injuries:
            row.state = InjuryState.PERMANENT
    await refresh(realm.session, RULES, soldier, ctx.epoch)
    await mind_skills(ctx)
    assert soldier.mortal_role is MortalRole.CAPTAIN
    mind = await realm.session.get(MindRow, soldier.id)
    assert mind is not None and mind.career_ended_epoch == ctx.epoch


async def test_relations_are_built_from_remembered_deeds_and_fade(realm: Realm) -> None:
    first, second = await people(realm, "Hill Folk"), await people(realm, "Marsh Folk")
    ctx = context(realm.session, epoch=5)
    assert await change_relation(ctx, first.id, second.id, -40, MemoryKind.FOUGHT_US, note="battle") == -40
    held = await memories_about(realm.session, first.id, second.id)
    assert held[0].kind is MemoryKind.FOUGHT_US and held[0].note == "battle"
    seen = await opinion(realm.session, RULES, 5, first.id, second.id)
    assert seen.value == -40 and seen.components[next(iter(seen.components))] is not None
    await mind_opinion(context(realm.session, epoch=25))
    later = await relation(realm.session, RULES, first.id, second.id)
    assert -40 < later <= 0
    assert await forget_faded(realm.session, RULES, 200) >= 1


async def test_a_culture_weighs_the_same_deed_by_what_it_values(realm: Realm) -> None:
    proud, humble = await people(realm, "Proud Folk"), await people(realm, "Easy Folk")
    raider = await people(realm, "Raiders")
    await write_values(realm.session, ValueHolder.CULTURE, proud.id, {ValueAxis.HONOUR: 90, ValueAxis.MERCY: 80})
    await write_values(realm.session, ValueHolder.CULTURE, humble.id, {ValueAxis.HONOUR: -90, ValueAxis.MERCY: -80})
    for victim in (proud, humble):
        await remember(realm.session, RULES, holder_id=victim.id, subject_id=raider.id, kind=MemoryKind.HARMED_ME, magnitude=-30, epoch=3)
    hurt = await opinion(realm.session, RULES, 3, proud.id, raider.id)
    shrug = await opinion(realm.session, RULES, 3, humble.id, raider.id)
    assert hurt.value < shrug.value


async def test_a_killing_leaves_grief_in_the_kin_and_memories_pass_on(realm: Realm) -> None:
    father = await mortal(realm, "Arn")
    daughter = await mortal(realm, "Ysa")
    killer = await mortal(realm, "Vorn")
    await link(realm.session, daughter.id, father.id, BondKind.DESCENDS_FROM)
    old_foe = await mortal(realm, "Grell")
    await remember(realm.session, RULES, holder_id=father.id, subject_id=old_foe.id, kind=MemoryKind.BETRAYED_ME, magnitude=-80, epoch=3)
    await die(context(realm.session), father, cause="was slain", killer_id=killer.id)
    grief = await memories_about(realm.session, daughter.id, killer.id)
    assert grief and grief[0].kind is MemoryKind.KILLED_KIN
    inherited = await memories_about(realm.session, daughter.id, old_foe.id)
    assert inherited and inherited[0].inherited_from_node_id == father.id
    assert abs(inherited[0].magnitude) == round(80 * RULES.memory.inherit_pct / 100)


async def test_strong_grief_sets_a_mortal_on_vengeance(realm: Realm) -> None:
    avenger = await mortal(realm, "Rhea", role=MortalRole.HERO)
    killer = await mortal(realm, "Morr", role=MortalRole.BANDIT)
    await remember(realm.session, RULES, holder_id=avenger.id, subject_id=killer.id, kind=MemoryKind.KILLED_KIN, magnitude=-90, epoch=3, decay_pct=0)
    await mind_memories(context(realm.session, tuned(memory={"vengeance_chance": 100})))
    quest = await realm.session.scalar(select(HeroQuestRow).where(HeroQuestRow.hero_entity_id == avenger.id))
    assert quest is not None and quest.kind is HeroQuestKind.VENGEANCE and quest.target_node_id == killer.id


async def test_pressures_come_from_the_state_of_a_community(realm: Realm) -> None:
    poor = await settlement(realm, "Mudhollow", prosperity=10)
    rich = await settlement(realm, "Goldmere", prosperity=90)
    folk = await people(realm, "Mud Folk")
    await mind_survey(context(realm.session))
    await mind_needs(context(realm.session))
    assert (await pressures_of(realm.session, poor.id))[PressureKind.POVERTY] > (await pressures_of(realm.session, rich.id))[PressureKind.POVERTY]
    assert (await pressures_of(realm.session, poor.id))[PressureKind.HUNGER] > 0
    assert PressureKind.IMPIETY in await pressures_of(realm.session, folk.id)


async def test_a_captive_feels_unsafe(realm: Realm) -> None:
    town = await settlement(realm, "Keep")
    free = await mortal(realm, "Lio", location_id=town.id)
    held = await mortal(realm, "Nim", location_id=town.id)
    await link(realm.session, town.id, held.id, BondKind.HOLDS_CAPTIVE)
    await mind_survey(context(realm.session))
    await mind_needs(context(realm.session))
    assert (await needs_of(realm.session, held.id))[NeedKind.SAFETY] < (await needs_of(realm.session, free.id))[NeedKind.SAFETY]


async def test_humiliation_and_a_wrathful_ruler_raise_the_drive_to_war(realm: Realm) -> None:
    folk = await people(realm, "Beaten Folk")
    calm = await war_drive(realm.session, RULES, folk.id)
    king = await mortal(realm, "Hosk", role=MortalRole.RULER)
    await link(realm.session, king.id, folk.id, BondKind.RULES)
    await ensure_mind_row(realm.session, king, 3)
    await add_trait(realm.session, king.id, TraitKind.WRATHFUL, TraitSource.PLAYER, 3)
    assert await war_drive(realm.session, RULES, folk.id) > calm


async def test_a_ruler_and_a_god_pull_a_culture_toward_themselves(realm: Realm) -> None:
    folk = await people(realm, "Pliant Folk")
    god = await son(realm.session, "Tor", realm.world.id)
    god.domain_primary, god.domain_secondary = Domain.WAR, Domain.BLOOD
    await link(realm.session, folk.id, god.id, BondKind.WORSHIPS)
    await mind_survey(context(realm.session))
    await write_values(realm.session, ValueHolder.CULTURE, folk.id, {ValueAxis.MARTIAL: -40, ValueAxis.PIETY: 60})
    before = (await values_for(realm.session, folk.id))[ValueAxis.MARTIAL]
    await mind_values(context(realm.session, epoch=4))
    assert (await values_for(realm.session, folk.id))[ValueAxis.MARTIAL] > before


async def test_the_same_god_and_close_values_warm_neighbours(realm: Realm) -> None:
    first, second, third = await people(realm, "One"), await people(realm, "Two"), await people(realm, "Three")
    await write_values(realm.session, ValueHolder.CULTURE, first.id, {ValueAxis.KINSHIP: 60})
    await write_values(realm.session, ValueHolder.CULTURE, second.id, {ValueAxis.KINSHIP: 55})
    await write_values(realm.session, ValueHolder.CULTURE, third.id, {ValueAxis.KINSHIP: -70, ValueAxis.MERCY: -60})
    assert await closeness(realm.session, first.id, second.id) > await closeness(realm.session, first.id, third.id)
    assert await relation(realm.session, RULES, first.id, second.id) > await relation(realm.session, RULES, first.id, third.id)
    assert await realm.session.scalar(select(CommunityRelationRow)) is None


async def test_a_healer_heals_by_skill_and_is_remembered(realm: Realm) -> None:
    healer = await mortal(realm, "Mira", role=MortalRole.HEALER)
    patient = await mortal(realm, "Bo", role=MortalRole.HERO)
    for node in (healer, patient):
        await ensure_mind_row(realm.session, node, 3)
    await set_skill(realm.session, healer.id, SkillKind.MEDICINE, 90, epoch=3, source=SkillSource.PLAYER)
    ctx = context(realm.session)
    await apply_hits(ctx, patient, Harm(15, HarmCause.BATTLE, "fell", part="left_leg", kind=InjuryKind.DEEP_CUT, severity=4), lethal=False)
    calm = tuned(healing={"infection_deep_cut": 0})
    for epoch in range(4, 14):
        await heal_wounds(context(realm.session, calm, epoch=epoch))
    medicine = (await skills_of(realm.session, healer.id))[SkillKind.MEDICINE]
    assert medicine.xp > 0 or medicine.level > 90
    saved = await memories_about(realm.session, patient.id, healer.id)
    assert saved and saved[0].kind is MemoryKind.SAVED_ME
    assert patient.status is EntityStatus.CANON


async def test_agents_hear_the_pressures_on_their_home_and_their_worshippers(realm: Realm) -> None:
    town = await settlement(realm, "Saltmere")
    smith = await mortal(realm, "Orla", location_id=town.id)
    god = await son(realm.session, "Velan", realm.world.id)
    await link(realm.session, town.id, god.id, BondKind.WORSHIPS)
    await write_pressures(realm.session, town.id, {PressureKind.HUNGER: 70, PressureKind.POVERTY: 50, PressureKind.IMPIETY: 10})
    rules = Rules()
    mortal_lines = await mind_lines(realm.session, rules, smith, 3, private=True)
    assert any(line.startswith("Your home Saltmere is pressed by: hunger 70/100, poverty 50/100") for line in mortal_lines)
    god_lines = await mind_lines(realm.session, rules, god, 3, private=True)
    assert any("Your worshippers Saltmere" in line and "hunger 70/100" in line for line in god_lines)


async def test_neighbours_judge_a_deed_by_their_own_values(realm: Realm) -> None:
    ctx = context(realm.session)
    raider = await people(realm, "Ash Riders")
    victim = await people(realm, "Reed Folk")
    gentle = await people(realm, "Dove Kin")
    fierce = await people(realm, "Wolf Kin")
    await write_values(realm.session, ValueHolder.CULTURE, gentle.id, {ValueAxis.MERCY: 90, ValueAxis.MARTIAL: -80})
    await write_values(realm.session, ValueHolder.CULTURE, fierce.id, {ValueAxis.MARTIAL: 90, ValueAxis.MERCY: -80})
    await change_relation(ctx, victim.id, raider.id, -20, MemoryKind.HARMED_ME, note="the burning of the reeds")
    gentle_view = sum(row.magnitude for row in await memories_about(realm.session, gentle.id, raider.id))
    fierce_view = sum(row.magnitude for row in await memories_about(realm.session, fierce.id, raider.id))
    assert gentle_view < 0 < fierce_view


async def test_a_faction_agenda_drifts_toward_its_people_and_its_members(realm: Realm) -> None:
    ctx = context(realm.session)
    folk = await people(realm, "Reed Folk")
    guild = await make(realm.session, "Reed Guild", EntityType.FACTION, FactionStats(sway=40), world_id=realm.world.id, location_id=realm.region.id)
    await link(realm.session, guild.id, folk.id, BondKind.MEMBER_OF)
    await ensure_mind_row(realm.session, guild, 1)
    await write_values(realm.session, ValueHolder.CULTURE, folk.id, {ValueAxis.WEALTH: 80})
    await write_values(realm.session, ValueHolder.AGENDA, guild.id, {ValueAxis.WEALTH: -80})
    await mind_values(ctx)
    assert (await stored_values(realm.session, ValueHolder.AGENDA, guild.id))[ValueAxis.WEALTH] > -80


def test_written_character_becomes_traits() -> None:
    assert read_depth("nature: a fearless and greedy smith, just a little shy") == [TraitKind.BRAVE, TraitKind.GREEDY, TraitKind.RECLUSIVE]
    assert read_depth("") == []


def test_every_trait_effect_is_read_by_a_mechanic() -> None:
    root = Path(__file__).resolve().parents[3] / "src" / "aerona"
    sources = " ".join(path.read_text() for folder in ("engine", "tools", "agents") for path in (root / folder).rglob("*.py"))
    unread = [effect for effect in TraitEffect if f"TraitEffect.{effect.name}" not in sources]
    assert unread == []


async def test_a_hard_people_leaves_its_broken_to_beg(realm: Realm) -> None:
    ctx = context(realm.session)
    hard = await people(realm, "Flint Folk")
    soft = await people(realm, "Dove Folk")
    await write_values(realm.session, ValueHolder.CULTURE, hard.id, {ValueAxis.MERCY: -60})
    await write_values(realm.session, ValueHolder.CULTURE, soft.id, {ValueAxis.MERCY: 60})
    flint_town, dove_town = await settlement(realm, "Flintholm"), await settlement(realm, "Dovecote")
    await link(realm.session, flint_town.id, hard.id, BondKind.DESCENDS_FROM)
    await link(realm.session, dove_town.id, soft.id, BondKind.DESCENDS_FROM)
    broken = await mortal(realm, "Garr", location_id=flint_town.id)
    spared = await mortal(realm, "Ilse", location_id=dove_town.id)
    assert await left_to_beg(ctx, broken)
    assert not await left_to_beg(ctx, spared)


async def test_a_rusted_skill_returns_fast_and_a_better_master_teaches_faster(realm: Realm) -> None:
    rules = Rules()
    rusty = await mortal(realm, "Orm")
    fresh = await mortal(realm, "Pell")
    row = await set_skill(realm.session, rusty.id, SkillKind.SPEAR, 10, epoch=1, source=SkillSource.PRACTICE)
    row.peak = 60
    await set_skill(realm.session, fresh.id, SkillKind.SPEAR, 10, epoch=1, source=SkillSource.PRACTICE)
    await practise(realm.session, rules, rusty.id, SkillKind.SPEAR, 40, epoch=2)
    await practise(realm.session, rules, fresh.id, SkillKind.SPEAR, 40, epoch=2)
    assert (await skills_of(realm.session, rusty.id))[SkillKind.SPEAR].level > (await skills_of(realm.session, fresh.id))[SkillKind.SPEAR].level


async def test_a_full_granary_feeds_a_starving_neighbour(realm: Realm) -> None:
    ctx = context(realm.session)
    rich = await settlement(realm, "Granary")
    poor = await settlement(realm, "Dustholm")
    await set_stock(realm.session, rich.id, Commodity.FOOD, 400)
    await set_stock(realm.session, poor.id, Commodity.FOOD, 0)
    await write_pressures(realm.session, poor.id, {PressureKind.HUNGER: 90})
    rules = tuned(needs={"famine_aid_chance": 100})
    await famine_aid(context(realm.session, rules))
    assert await stock(realm.session, rules, poor.id, Commodity.FOOD) > 0
    assert [row.kind for row in await memories_about(realm.session, poor.id, rich.id)] == [MemoryKind.FAMINE_AID]
    assert ctx.rules.needs.famine_aid_share_pct


async def test_a_ruler_who_hates_the_neighbour_sours_the_relation(realm: Realm) -> None:
    ctx = context(realm.session)
    home = await people(realm, "Reed Folk")
    other = await people(realm, "Ash Folk")
    calm = await relation(realm.session, ctx.rules, home.id, other.id)
    king = await mortal(realm, "Vorn")
    await link(realm.session, king.id, home.id, BondKind.RULES)
    await remember(realm.session, ctx.rules, holder_id=king.id, subject_id=other.id, kind=MemoryKind.KILLED_KIN, magnitude=-90, epoch=ctx.epoch)
    assert await refresh_relation(realm.session, ctx.rules, ctx.epoch, home.id, other.id) < calm
