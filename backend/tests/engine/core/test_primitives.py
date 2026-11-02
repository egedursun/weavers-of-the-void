from dataclasses import replace

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.sons import PowerDraft, SonRepository
from aerona.db.tables.society import ReverenceRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.son import PowerEffect
from aerona.domain.models.entity_stats import ItemStats, PeopleStats, SpeciesStats
from aerona.engine.primitives.capacity import CapacityModel, carrying_capacity
from aerona.engine.primitives.distance import RegionAtlas, seafaring_reach
from aerona.engine.primitives.essence import overflow_to_land
from aerona.engine.primitives.faith import change_religion, first_faith_god, son_faith, worship_creator
from aerona.engine.primitives.knowledge import level_multiplier
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.prosperity import add_prosperity, prosperity_gain
from aerona.engine.primitives.queries import has_flag
from aerona.engine.primitives.stats import stat
from aerona.engine.primitives.strength import ally_strength, military_strength, patron_bonus, tamed_power, weapon_power
from aerona.engine.primitives.thresholds import percentile_threshold, relative_threshold
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, add_flag, bond, entity, knowledge, settlement, son_draft


def test_rounding_is_half_up() -> None:
    assert round_half_up(2.5) == 3
    assert clamp_int(-4, 0, 100) == 0
    assert clamp_int(100.6, 0, 100) == 100


def test_prosperity_gain_diminishes_above_equilibrium(rules: Rules) -> None:
    target = rules.world_effects.prosperity_target
    assert prosperity_gain(rules, target - 10, 6) == 6
    assert prosperity_gain(rules, 100, 6) == 0
    assert prosperity_gain(rules, 75, 10) == 10 * 25 / (100 - target)
    assert prosperity_gain(rules, 80, -5) == -5


async def test_add_prosperity_clamps(world: CoreWorld, rules: Rules) -> None:
    assert add_prosperity(rules, world.people, 1000) == 100
    assert add_prosperity(rules, world.regions[0], 5) is None


def test_percentile_threshold_stays_within_bounds() -> None:
    assert percentile_threshold([10, 20, 30, 90], 0.8, 40, 55) == 55
    assert percentile_threshold([10, 20, 30, 45], 0.8, 40, 55) == 45
    assert percentile_threshold([], 0.8, 40, 55) == 55


async def test_relative_threshold_is_per_world(world: CoreWorld, session: AsyncSession) -> None:
    other = await entity(session, "Sharpfang", EntityType.SPECIES, SpeciesStats(danger=50), world_id=world.world.id, location_id=world.regions[1].id)
    threshold = relative_threshold([world.species, other], "danger", 0.8, 40, 55)
    assert threshold(world.species) == 50


async def test_region_atlas_hops_and_reach(world: CoreWorld, session: AsyncSession) -> None:
    near_town = await settlement(session, "Brookhold", world, world.regions[1])
    far_town = await settlement(session, "Farhold", world, world.regions[3])
    atlas = await RegionAtlas.load(session)
    assert atlas.top_region(near_town.id) == world.regions[1].id
    assert atlas.hops(world.people.id, near_town.id) == 1
    assert atlas.hops(world.people.id, far_town.id) == 3
    assert atlas.adjacent(world.people.id, near_town.id)
    assert not atlas.near(world.people.id, world.species.id, None)
    assert atlas.near(world.people.id, world.species.id, seafaring_reach(Rules(), seafaring=True, sea_ban=False))
    assert seafaring_reach(Rules(), seafaring=True, sea_ban=True) is None
    assert not atlas.same_region(world.language.id, world.language.id)


async def test_capacity_blends_place_and_region(world: CoreWorld, session: AsyncSession, rules: Rules) -> None:
    model = await CapacityModel.load(session, rules)
    assert model.effective_fertility(world.people) == 70
    reading = await carrying_capacity(session, rules, world.people)
    assert reading is not None
    assert reading.region_id == world.regions[0].id
    assert reading.sharing == 1
    assert reading.region_population == 6000
    assert reading.capacity > reading.region_population
    assert await carrying_capacity(session, rules, world.species) is None


async def test_military_strength_counts_weapons_knowledge_and_allies(world: CoreWorld, session: AsyncSession, rules: Rules) -> None:
    base = await military_strength(session, rules, world.people)
    sword = await entity(
        session, "Oathblade", EntityType.ITEM, ItemStats(damage=80, protection=20, might=40), world_id=world.world.id, location_id=world.regions[0].id
    )
    await bond(session, world.people.id, sword.id, BondKind.OWNS)
    war = await knowledge(session, world, "Shieldwall", KnowledgeBranch.WARFARE)
    await bond(session, world.people.id, war.id, BondKind.KNOWS)
    armed = await military_strength(session, rules, world.people)
    warcraft = rules.world_war_strength.warcraft_bonus * level_multiplier(rules.knowledge, 2)
    assert armed == base + await weapon_power(session, rules, world.people.id) + warcraft
    friend = await entity(
        session, "Vellish", EntityType.PEOPLE, PeopleStats(population=900, martiality=50), world_id=world.world.id, location_id=world.regions[1].id
    )
    await bond(session, world.people.id, friend.id, BondKind.ALLY)
    share = await ally_strength(session, rules, world.people)
    assert share == await military_strength(session, rules, friend) * rules.world_war_strength.ally_share_pct / 100


async def test_tamed_beasts_and_war_father(world: CoreWorld, session: AsyncSession, rules: Rules) -> None:
    await bond(session, world.people.id, world.species.id, BondKind.TAMED)
    creatures = rules.creatures
    assert await tamed_power(session, rules, world.people.id) == creatures.tamed_war_base + round_half_up(40 / creatures.tamed_strength_divisor)
    plain = await patron_bonus(session, rules, world.people)
    await SonRepository(session).set_powers(world.son.id, [PowerDraft("War Father", "Leads armies.", PowerEffect.WAR_FATHER)])
    fathered = await patron_bonus(session, rules, world.people)
    assert fathered.bonus == round_half_up(world.son.strength / rules.world_war_strength.patron_strength_divisor * rules.world_war_strength.war_father_mult)
    assert plain.bonus == round_half_up(world.son.strength / rules.world_war_strength.patron_strength_divisor)


async def test_overflow_fertilises_the_most_barren_regions(world: CoreWorld, session: AsyncSession) -> None:
    rules = Rules()
    rules = replace(rules, essence=replace(rules.essence, overflow_per_fertility=1, overflow_fertility_cap=50))
    result = await overflow_to_land(session, rules, 3)
    assert result.budget == 3
    assert result.given == 3
    assert stat(world.regions[3], "fertility") == 48


async def test_son_faith_counts_worshippers_and_multiplier(world: CoreWorld, session: AsyncSession, rules: Rules) -> None:
    faith = await son_faith(session, rules, world.son)
    assert faith == round_half_up(6000 / rules.faith.pious_population_per_faith * 60 / 100)
    await SonRepository(session).set_powers(world.son.id, [PowerDraft("Beloved", "Worshipped.", PowerEffect.WORSHIPPED)])
    assert await son_faith(session, rules, world.son) == round_half_up(faith * rules.faith.multiplier_power_pct / 100)


async def test_son_faith_counts_reverences_at_their_weight(world: CoreWorld, session: AsyncSession, rules: Rules) -> None:
    rival = await SonRepository(session).create(son_draft("Varos", world.world.id, (Domain.WAR, Domain.FIRE)))
    assert await son_faith(session, rules, rival) == 0
    assert await change_religion(session, world.people, rival.id, 2, "a shared feast", syncretic=True)
    full = 6000 / rules.faith.pious_population_per_faith * 60 / 100
    assert await son_faith(session, rules, rival) == round_half_up(full * rules.religion.reverence_weight_pct / 100)
    assert await son_faith(session, rules, world.son) == round_half_up(full)


async def test_religion_change_and_syncretism(world: CoreWorld, session: AsyncSession) -> None:
    rival = await SonRepository(session).create(son_draft("Varos", world.world.id, (Domain.WAR, Domain.FIRE)))
    assert await change_religion(session, world.people, rival.id, 2, "a vision", syncretic=True)
    assert await session.get(ReverenceRow, (world.people.id, rival.id)) is not None
    await add_flag(session, world.people.id, EntityFlag.GODLESS)
    assert await change_religion(session, world.people, rival.id, 2, "a vision")
    assert not await has_flag(session, world.people.id, EntityFlag.GODLESS)
    assert not await change_religion(session, world.people, rival.id, 2, "again")


async def test_worship_creator_and_first_god(world: CoreWorld, session: AsyncSession, rules: Rules) -> None:
    town = await settlement(session, "Brookhold", world, world.regions[1])
    atlas = await RegionAtlas.load(session)
    assert (await first_faith_god(session, rules, town, atlas, 0.0)) == world.son
    await add_flag(session, town.id, EntityFlag.GODLESS)
    assert await worship_creator(session, town, 2, "a sign")
    assert not await has_flag(session, town.id, EntityFlag.GODLESS)
    assert not await worship_creator(session, town, 2, "a sign")
