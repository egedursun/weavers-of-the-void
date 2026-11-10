from dataclasses import replace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.divine import DivineStandingRow
from aerona.db.tables.dominion import CreatureLessonRow, DivineCreatureRow, DominionRow, GodImageRow, MagicSiteRow, RegionDominionRow, ThroneRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import ModifierRow
from aerona.db.tables.lore import FolkBeliefRow
from aerona.db.tables.mind import SkillRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.dominion import (
    BeliefStance,
    CreatureDeed,
    CreatureLesson,
    DivineScale,
    MagicSiteKind,
    PerceivedAlignment,
    PrayerTone,
    WorshipMode,
)
from aerona.domain.enums.entity import EntityStatus, MortalRole
from aerona.domain.enums.gathering import GatheringKind, GatheringStatus
from aerona.domain.enums.mind import Facet, SkillKind, SkillSource
from aerona.domain.enums.rarity import Rarity
from aerona.engine.context import TickContext
from aerona.engine.divine.avatars import manifest
from aerona.engine.divine.goals import ascend
from aerona.engine.dominion import control
from aerona.engine.dominion.blame import blame_rulers
from aerona.engine.dominion.core import DominionTally, gather, weigh_dominion
from aerona.engine.dominion.creatures import choose
from aerona.engine.dominion.curses import curse_desecrator
from aerona.engine.dominion.design import Design, budget_of, fate_check
from aerona.engine.dominion.effects import divine_power, scale_here, step_here
from aerona.engine.dominion.image import ImageTally, read_image, shape
from aerona.engine.dominion.miracles import belief_of, impress, witness_count
from aerona.engine.dominion.sites import SiteTally, can_search, search_chance, tend_thrones
from aerona.engine.dominion.worship import WorshipTally, mode_of, perceived_of, prayer_tone, view_worship
from aerona.engine.gatherings import control as gathering_control
from aerona.engine.mind.split import facets_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import set_stats, stat
from aerona.rules.registry import Rules
from aerona.services.integrity.dominion_links import mend_dominion_links
from tests.engine.core.factories import CoreWorld, bond, mortal, settlement


async def worshipped(session: AsyncSession, world: CoreWorld, name: str = "Velm") -> int:
    town = await settlement(session, name, world, world.regions[0])
    await bond(session, town.id, world.son.id, BondKind.WORSHIPS)
    return town.id


async def test_worship_gives_its_god_dominion_and_the_god_rules_the_region(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    await worshipped(session, world)
    await weigh_dominion(ctx, DominionTally())
    claim = await session.get(DominionRow, (world.son.id, world.regions[0].id))
    assert claim is not None
    assert claim.worship > 0
    assert claim.strength > 0
    ruler = await session.get(RegionDominionRow, world.regions[0].id)
    assert ruler is not None
    assert ruler.god_node_id == world.son.id


async def test_a_held_dominion_stays_where_the_god_set_it(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    await worshipped(session, world)
    await control.set_dominion(ctx, world.son.id, world.regions[0].id, 7, hold=True)
    await weigh_dominion(ctx, DominionTally())
    claim = await session.get(DominionRow, (world.son.id, world.regions[0].id))
    assert claim is not None
    assert claim.strength == 7


async def test_the_ruling_gods_scales_lean_its_land(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    await worshipped(session, world)
    await control.set_dominion(ctx, world.son.id, world.regions[0].id, 100, hold=True)
    await control.set_scale(ctx, world.son.id, DivineScale.ORDER, -3, hold=True)
    await weigh_dominion(ctx, DominionTally())
    keys = set(await session.scalars(select(ModifierRow.target_key).where(ModifierRow.reason_key.like("dominion.%"))))
    assert "danger" in keys


def test_belief_grows_with_witnesses_need_and_novelty(ctx: TickContext) -> None:
    alone = belief_of(ctx, magnitude=100, witnesses=1, need=0, novelty=100, legibility=100)
    crowd = belief_of(ctx, magnitude=100, witnesses=200, need=0, novelty=100, legibility=100)
    needed = belief_of(ctx, magnitude=100, witnesses=200, need=100, novelty=100, legibility=100)
    stale = belief_of(ctx, magnitude=100, witnesses=200, need=100, novelty=25, legibility=100)
    assert alone < crowd < needed
    assert stale < needed


async def test_a_repeated_miracle_impresses_less(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    town = await worshipped(session, world)
    target = await mortal(session, "Ossa", world, town)
    first = await impress(ctx, world.son.id, target, kind="heal", magnitude=80, witnesses=50)
    second = await impress(ctx, world.son.id, target, kind="heal", magnitude=80, witnesses=50)
    assert second.novelty < first.novelty
    assert second.belief <= first.belief


async def test_a_miracle_in_another_gods_land_is_credited_to_its_ruler(session: AsyncSession, world: CoreWorld, rules: Rules) -> None:
    certain = replace(rules, miracle_impression=replace(rules.miracle_impression, misread_pct=100))
    ctx = await manual_context(session, "misread", rules=certain)
    await worshipped(session, world)
    await control.set_dominion(ctx, world.creator.id, world.regions[0].id, 100, hold=True)
    await weigh_dominion(ctx, DominionTally())
    target = await mortal(session, "Brann", world, world.regions[0].id)
    row = await impress(ctx, world.son.id, target, kind="heal", magnitude=80, witnesses=20)
    assert row.credited_node_id in {world.son.id, world.creator.id}
    assert row.god_node_id == world.son.id


async def test_a_feared_god_is_appeased_and_prayed_to_for_mercy(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    assert perceived_of(ctx.rules, love=80, fear=10) is PerceivedAlignment.BENEVOLENT
    assert perceived_of(ctx.rules, love=10, fear=80) is PerceivedAlignment.MALEVOLENT
    assert mode_of(ctx.rules, love=10, fear=90) is WorshipMode.APPEASEMENT
    town = await worshipped(session, world)
    session.add(DivineStandingRow(community_entity_id=town, god_node_id=world.son.id, awe=40, love=5, fear=90, neglect=0, epoch=0, locked=[]))
    await session.flush()
    await view_worship(ctx, WorshipTally())
    standing = await session.get(DivineStandingRow, (town, world.son.id))
    assert standing is not None
    assert standing.perceived is PerceivedAlignment.MALEVOLENT
    assert standing.mode is WorshipMode.APPEASEMENT
    pilgrim = await mortal(session, "Ide", world, town)
    assert await prayer_tone(session, pilgrim, world.son.id) is PrayerTone.MERCY


async def test_belief_pulls_a_gods_temper_unless_it_resists(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    son = world.son
    son.wrath = 10
    row = GodImageRow(god_node_id=son.id, believed_wrath=100, believed_mercy=0, pull=50, stance=BeliefStance.YIELD, locked=[])
    session.add(row)
    await session.flush()
    await shape(ctx, son, row, ImageTally())
    pulled = son.wrath
    assert pulled > 10
    son.essence = 1000
    row.stance = BeliefStance.RESIST
    tally = ImageTally()
    await shape(ctx, son, row, tally)
    assert son.wrath == pulled
    assert son.essence < 1000
    assert tally.resisted == 1


async def test_a_divine_creature_learns_from_reward_and_punishment(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    creature = await control.raise_divine_creature(ctx, world.son.id, name="Harrow", description="", home_id=world.regions[0].id)
    start = creature.weights[CreatureDeed.HEAL_SICK.value]
    await control.teach_creature(ctx, creature.creature_entity_id, CreatureDeed.HEAL_SICK, CreatureLesson.REWARD)
    assert creature.weights[CreatureDeed.HEAL_SICK.value] > start
    harsh = creature.weights[CreatureDeed.HUNT_FOLK.value]
    await control.teach_creature(ctx, creature.creature_entity_id, CreatureDeed.HUNT_FOLK, CreatureLesson.PUNISH)
    assert creature.weights[CreatureDeed.HUNT_FOLK.value] < harsh
    lessons = list(await session.scalars(select(CreatureLessonRow).where(CreatureLessonRow.creature_entity_id == creature.creature_entity_id)))
    assert {lesson.lesson for lesson in lessons} == {CreatureLesson.REWARD, CreatureLesson.PUNISH}
    assert choose(ctx, creature) in set(CreatureDeed)


def test_a_design_that_overspends_is_trimmed_and_costs_the_gods_powers(rules: Rules) -> None:
    budget = budget_of(rules, Rarity.COMMON, 1)
    lavish = Design(dominion_strength=100, magic_aptitude=100, manifestation_strength=100, scales={DivineScale.ORDER: 3})
    checked = fate_check(rules, budget, lavish)
    assert checked.spent <= budget
    assert checked.design.dominion_strength < 100
    modest = fate_check(rules, budget, Design())
    assert modest.stats_pct > checked.stats_pct


async def test_a_throne_passes_to_the_god_who_rules_its_land(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    await worshipped(session, world)
    await control.set_dominion(ctx, world.son.id, world.regions[0].id, 100, hold=True)
    await weigh_dominion(ctx, DominionTally())
    throne = await control.create_throne(ctx, world.regions[0].id, 80, None)
    essence = world.son.essence
    await tend_thrones(ctx, SiteTally())
    assert throne.holder_node_id == world.son.id
    assert world.son.essence > essence


async def test_a_second_throne_at_the_same_place_is_refused(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    await control.create_throne(ctx, world.regions[0].id, 60, None)
    with pytest.raises(ValidationFailedError):
        await control.create_throne(ctx, world.regions[0].id, 60, None)
    assert len(list(await session.scalars(select(ThroneRow).where(ThroneRow.place_entity_id == world.regions[0].id)))) == 1


async def test_a_magic_site_is_found_once(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    site = await control.create_site(ctx, world.regions[0].id, MagicSiteKind.SOURCE, MagicSchool.LIFE, 60, found_now=False)
    assert site.found_epoch is None
    await control.reveal_site(ctx, site.id, None)
    found = await session.get(MagicSiteRow, site.id)
    assert found is not None
    assert found.found_epoch is not None
    with pytest.raises(ValidationFailedError):
        await control.reveal_site(ctx, site.id, None)


async def test_a_desecrator_is_cursed_by_the_keepers_god(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    keeper = await worshipped(session, world, "Orrin")
    thief = await mortal(session, "Skel", world, world.regions[0].id)
    await curse_desecrator(ctx, keeper, thief.id)
    curses = list(await session.scalars(select(AfflictionRow).where(AfflictionRow.bearer_node_id == thief.id)))
    assert curses


async def ruled_by_son(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> int:
    town = await worshipped(session, world)
    await control.set_dominion(ctx, world.son.id, world.regions[0].id, 100, hold=True)
    await weigh_dominion(ctx, DominionTally())
    return town


async def test_a_disaster_in_a_dominated_land_is_blamed_on_its_ruler(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    town = await ruled_by_son(ctx, session, world)
    session.add(DivineStandingRow(community_entity_id=town, god_node_id=world.son.id, awe=0, love=50, fear=10, neglect=0, epoch=0, locked=[]))
    await session.flush()
    assert await blame_rulers(ctx, [town]) == 1
    standing = await session.get(DivineStandingRow, (town, world.son.id))
    assert standing is not None
    assert standing.fear > 10
    assert standing.love < 50


async def test_dominion_and_magic_aptitude_strengthen_the_rites_of_the_faithful(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    town = await ruled_by_son(ctx, session, world)
    await control.edit_design(ctx, world.son.id, {"magic_aptitude": 100}, [])
    gifted = await divine_power(ctx, world.son.id, town, ctx.rules.dominion.rite_power_pct)
    await control.edit_design(ctx, world.son.id, {"magic_aptitude": 0}, [])
    giftless = await divine_power(ctx, world.son.id, town, ctx.rules.dominion.rite_power_pct)
    assert gifted > 1.0
    assert giftless < gifted


async def test_the_scales_of_the_ruler_move_healing_and_output(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    town = await ruled_by_son(ctx, session, world)
    await control.set_scale(ctx, world.son.id, DivineScale.GROWTH, 3, hold=True)
    await control.set_scale(ctx, world.son.id, DivineScale.PRODUCTIVITY, -2, hold=True)
    assert await step_here(ctx, town, DivineScale.GROWTH, ctx.rules.dominion.healing_per_step_pct) > 1.0
    assert await step_here(ctx, town, DivineScale.PRODUCTIVITY, ctx.rules.dominion.output_per_step_pct) < 1.0
    assert await scale_here(ctx, town, DivineScale.GROWTH) == 3


async def test_a_god_learns_where_it_is_losing_ground(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    await control.set_dominion(ctx, world.son.id, world.regions[1].id, 90, hold=False)
    await weigh_dominion(ctx, DominionTally())
    claim = await session.get(DominionRow, (world.son.id, world.regions[1].id))
    assert claim is not None
    assert claim.trend < 0


async def test_more_worshippers_give_more_dominion(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    small = await settlement(session, "Hollin", world, world.regions[1], population=50)
    await bond(session, small.id, world.son.id, BondKind.WORSHIPS)
    gathered = await gather(ctx, await RegionAtlas.load(session))
    few = gathered.sources[(world.son.id, world.regions[1].id)].worship
    assert 0 < few < ctx.rules.dominion.worship_weight
    set_stats(small, population=ctx.rules.dominion.worship_population * 10)
    await session.flush()
    gathered = await gather(ctx, await RegionAtlas.load(session))
    assert gathered.sources[(world.son.id, world.regions[1].id)].worship == ctx.rules.dominion.worship_weight


async def test_a_held_throne_awes_the_communities_of_its_whole_world(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    await ruled_by_son(ctx, session, world)
    far = await settlement(session, "Farhold", world, world.regions[1])
    await control.create_throne(ctx, world.regions[0].id, 80, world.son.id)
    await tend_thrones(ctx, SiteTally())
    standing = await session.get(DivineStandingRow, (far.id, world.son.id))
    assert standing is not None
    assert standing.awe > 0


async def test_belief_moves_a_gods_temperament(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    row = GodImageRow(god_node_id=world.son.id, believed_wrath=100, believed_mercy=0, pull=80, stance=BeliefStance.YIELD, locked=[])
    session.add(row)
    await session.flush()
    await shape(ctx, world.son, row, ImageTally())
    facets = await facets_of(session, world.son.id)
    assert facets[Facet.ANGER] > 0
    assert facets[Facet.ALTRUISM] < 0


async def test_folk_stories_firm_a_gods_image(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    town = await worshipped(session, world)
    session.add(DivineStandingRow(community_entity_id=town, god_node_id=world.son.id, awe=40, love=80, fear=5, neglect=0, epoch=0, locked=[]))
    await session.flush()
    await read_image(ctx, world.son, ImageTally())
    loose = await session.get(GodImageRow, world.son.id)
    assert loose is not None
    before = loose.intensity
    session.add(FolkBeliefRow(people_entity_id=world.people.id, god_node_id=world.son.id, account="told by the elders", epoch=0))
    await session.flush()
    await read_image(ctx, world.son, ImageTally())
    assert loose.intensity > before


async def test_only_a_mage_of_the_sites_school_or_an_explorer_can_find_it(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    site = await control.create_site(ctx, world.regions[0].id, MagicSiteKind.WARD, MagicSchool.WARDING, 60, found_now=False)
    mage = await mortal(session, "Wen", world, world.regions[0].id)
    session.add(SkillRow(holder_node_id=mage.id, skill=SkillKind.SPELLCRAFT, level=90, peak=90, last_used_epoch=1, source=SkillSource.PRACTICE))
    scout = await mortal(session, "Ruel", world, world.regions[0].id)
    scout.mortal_role = MortalRole.EXPLORER
    session.add(SkillRow(holder_node_id=scout.id, skill=SkillKind.TRACKING, level=90, peak=90, last_used_epoch=1, source=SkillSource.PRACTICE))
    await session.flush()
    assert await can_search(ctx, mage)
    assert await search_chance(ctx, mage, site) == 0
    assert await search_chance(ctx, scout, site) == ctx.rules.magic_sites.explorer_search_pct


async def test_ascending_raises_a_sons_level_toward_new_power_slots(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    await control.edit_design(ctx, world.son.id, {"rank": 0}, ["rank"])
    level = world.son.level
    await ascend(ctx, world.son)
    assert world.son.level == level + ctx.rules.god_design.rank_levels


async def test_manifestation_strength_sets_the_body_of_a_gods_mortal_form(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    town = await worshipped(session, world)
    place = await session.get(EntityRow, town)
    assert place is not None
    await control.edit_design(ctx, world.son.id, {"manifestation_strength": 0}, [])
    avatar = await manifest(ctx, world.son, place)
    assert stat(avatar, "hp") == round(ctx.rules.avatars.hp * ctx.rules.god_design.manifestation_floor_pct / 100)


async def test_the_guests_of_a_gathering_witness_a_miracle(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    target = await mortal(session, "Pell", world, world.regions[0].id)
    guests = [await mortal(session, f"Guest {number}", world, world.regions[0].id) for number in range(3)]
    gathering = await gathering_control.convene(
        ctx, target.id, GatheringKind.FEAST, place_id=None, honoured_id=None, milestone=None, guests=[guest.id for guest in guests], hold_now=True
    )
    assert gathering.status is not GatheringStatus.PLANNED
    assert await witness_count(ctx, target) > 1


async def test_dominion_links_of_fallen_gods_and_vanished_creatures_are_mended(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    creature = await control.raise_divine_creature(ctx, world.son.id, name="Morrow", description="", home_id=world.regions[0].id)
    beast = await session.get(EntityRow, creature.creature_entity_id)
    assert beast is not None
    beast.status = EntityStatus.DEAD
    beast.end_epoch = ctx.epoch
    await session.flush()
    assert await mend_dominion_links(session) >= 1
    assert await session.get(DivineCreatureRow, creature.creature_entity_id) is None
