from sqlalchemy import select

from aerona.db.tables.mind import MindRow
from aerona.db.tables.society import CommunityRelationRow
from aerona.db.tables.warfare import HeroQuestRow
from aerona.domain.enums.body import HarmCause, InjuryKind, InjuryState
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityStatus, MortalRole
from aerona.domain.enums.mind import ActKind, MemoryKind, NeedKind, PressureKind, SkillKind, SkillSource, TraitKind, TraitSource, ValueAxis, ValueHolder
from aerona.domain.enums.war import HeroQuestKind
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
    write_values,
)
from aerona.engine.mind.drives import closeness, war_drive
from aerona.engine.mind.memories import forget_faded, memories_about, remember
from aerona.engine.mind.opinion import opinion
from aerona.engine.mind.skills import practise, weather_skills
from aerona.engine.mind.space import value_distance, value_reading
from aerona.engine.phases.mind import mind_memories, mind_needs, mind_opinion, mind_skills, mind_survey, mind_values
from aerona.engine.services.community_relations import change_relation, relation
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, link, mortal, people, settlement, son, tuned

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
