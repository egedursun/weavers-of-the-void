from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.mortal import AGENT_TYPES
from aerona.core.random import SeededRandom
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.body import BodyRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.ecology import BeastProfileRow, HerdRow, SpeciesHostRow, SpeciesProfileRow, SpeciesRangeRow, SpeciesYieldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.polity import TreatyClauseRow, TreatyProfileRow
from aerona.domain.enums.body import BodyBuild, BodyPlan, HeightClass
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.disease import OutbreakStatus, SpreadPath
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.ecology import BeastTemper, Diet, DomesticationStage, SizeClass, Sociality, SpeciesUse, YieldProduct
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import CoastKind, RiverClass, SoilKind, TemperatureBand, TerrainKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.polity import ClauseKind, TreatyStatus
from aerona.domain.enums.society import CreatureTrait
from aerona.domain.models.entity_stats import BeastStats, DiseaseStats, ItemStats, MortalStats, PeopleStats, SettlementStats, SpeciesStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.routes import has_tamed_mount
from aerona.engine.ecology import beasts
from aerona.engine.ecology.domestication import drifted_size, stage_from_herds
from aerona.engine.ecology.foodweb import derive_links
from aerona.engine.ecology.hosts import acquire_immunity
from aerona.engine.ecology.profiles import SpeciesSpec, assign_traits, profile_of, traits_from_nature, typed_nature_backfill
from aerona.engine.ecology.ranges import load_wilds, overall
from aerona.engine.ecology.totems import found_totem, hunt_gods
from aerona.engine.economy.stocks import GoodsLedger
from aerona.engine.phases.creatures import speciation
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region, make_son, tick, tuned


async def land(session: AsyncSession, region_id: int, world_id: int, terrain: TerrainKind, temperature: int) -> RegionEnvironmentRow:
    row = RegionEnvironmentRow(
        entity_id=region_id,
        world_id=world_id,
        dominant_terrain=terrain,
        elevation_mean=20,
        roughness=10,
        latitude=40,
        moisture=60,
        base_forest=40,
        forest_cover=40,
        base_wetland=10,
        wetland=10,
        river_class=RiverClass.NONE,
        coast_kind=CoastKind.NONE,
        soil=SoilKind.LOAM,
        soil_fertility=60,
        soil_base=60,
        temperature=temperature,
        temperature_band=TemperatureBand.TEMPERATE,
        rainfall=50,
        seasonality=10,
        disease_load=0,
        magic_density=0,
        defensibility=20,
        locked=[],
    )
    session.add(row)
    await session.flush()
    return row


def ranges(session: AsyncSession, species_id: int, *region_ids: int, abundance: int = 50, since: int = 0) -> None:
    session.add_all(
        [SpeciesRangeRow(species_entity_id=species_id, region_entity_id=region, abundance=abundance, since_epoch=since, locked=[]) for region in region_ids]
    )


async def kind(ctx: TickContext, cosmos: Cosmos, name: str, region_id: int, spec: SpeciesSpec, **stats: int) -> EntityRow:
    species = await make_entity(ctx.session, name, EntityType.SPECIES, SpeciesStats(**stats), world_id=cosmos.home.id, location_id=region_id)
    await profile_of(ctx, species, spec)
    return species


async def test_a_profile_is_built_from_typed_fields_and_never_from_its_words(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Moor", cosmos.home.id)
    species = await make_entity(
        ctx.session,
        "Night Silk Wolf",
        EntityType.SPECIES,
        SpeciesStats(strength=20, danger=10),
        world_id=cosmos.home.id,
        location_id=region.id,
    )
    species.description = "A migratory pack of nocturnal wolves that spin silk and breathe dragon fire."
    row = await profile_of(ctx, species)
    assert row.diet is Diet.HERBIVORE and row.sociality is Sociality.HERD
    assert not row.nocturnal and not row.migratory and row.body_plan is BodyPlan.QUADRUPED
    products = set(await ctx.session.scalars(select(SpeciesYieldRow.product).where(SpeciesYieldRow.species_entity_id == species.id)))
    assert "silk" not in products and "dragonbone" not in products
    typed = await kind(
        ctx,
        cosmos,
        "Glimmerspinner",
        region.id,
        SpeciesSpec(BodyPlan.INSECTOID, SizeClass.TINY, Diet.CARNIVORE, Sociality.HIVE, True, True, (YieldProduct.SILK,)),
    )
    shaped = await ctx.session.get(SpeciesProfileRow, typed.id)
    assert shaped is not None and shaped.body_plan is BodyPlan.INSECTOID and shaped.size_class is SizeClass.TINY
    assert shaped.nocturnal and shaped.migratory and shaped.sociality is Sociality.HIVE
    made = set(await ctx.session.scalars(select(SpeciesYieldRow.product).where(SpeciesYieldRow.species_entity_id == typed.id)))
    assert {"silk", "chitin"} <= made


async def test_a_child_kind_inherits_its_parents_typed_nature(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Fen", cosmos.home.id)
    parent = await kind(ctx, cosmos, "Fen Strider", region.id, SpeciesSpec(BodyPlan.AVIAN, SizeClass.LARGE, Diet.SCAVENGER, Sociality.PACK, True, True))
    child = await make_entity(ctx.session, "Lesser Strider", EntityType.SPECIES, SpeciesStats(), world_id=cosmos.home.id, location_id=region.id)
    await BondRepository(ctx.session).connect(BondDraft(child.id, parent.id, BondKind.DESCENDS_FROM, ctx.epoch, "evolution"))
    row = await profile_of(ctx, child)
    assert (row.body_plan, row.size_class, row.diet, row.sociality, row.nocturnal, row.migratory) == (
        BodyPlan.AVIAN,
        SizeClass.LARGE,
        Diet.SCAVENGER,
        Sociality.PACK,
        True,
        True,
    )


async def test_traits_come_from_typed_nature(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Hive Hills", cosmos.home.id)
    swarm = await kind(ctx, cosmos, "Hivelings", region.id, SpeciesSpec(BodyPlan.AVIAN, SizeClass.SMALL, Diet.HERBIVORE, Sociality.HIVE), intelligence=10)
    profile = await ctx.session.get(SpeciesProfileRow, swarm.id)
    assert profile is not None and traits_from_nature(profile) == [CreatureTrait.FLYING, CreatureTrait.HIVE_MIND]
    assert await assign_traits(ctx, swarm) == [CreatureTrait.FLYING, CreatureTrait.HIVE_MIND]
    assert swarm.stats.intelligence == 10 + ctx.rules.creatures.hive_mind_intelligence
    assert await assign_traits(ctx, swarm) == []


async def test_the_food_web_is_derived_from_diet_size_and_shared_land(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Grass Sea", cosmos.home.id)
    far = await make_region(ctx.session, "Far Shore", cosmos.home.id)
    wolf = await kind(ctx, cosmos, "Duskwolf", region.id, SpeciesSpec(BodyPlan.QUADRUPED, SizeClass.MEDIUM, Diet.CARNIVORE, Sociality.PACK))
    deer = await kind(ctx, cosmos, "Glimdeer", region.id, SpeciesSpec(BodyPlan.QUADRUPED, SizeClass.MEDIUM, Diet.HERBIVORE))
    hare = await kind(ctx, cosmos, "Moonhare", region.id, SpeciesSpec(BodyPlan.QUADRUPED, SizeClass.SMALL, Diet.HERBIVORE))
    titan = await kind(ctx, cosmos, "Stonebeast", region.id, SpeciesSpec(BodyPlan.COLOSSAL, SizeClass.COLOSSAL, Diet.HERBIVORE))
    elk = await kind(ctx, cosmos, "Far Elk", far.id, SpeciesSpec(BodyPlan.QUADRUPED, SizeClass.MEDIUM, Diet.HERBIVORE))
    ranges(ctx.session, wolf.id, region.id)
    ranges(ctx.session, deer.id, region.id)
    ranges(ctx.session, hare.id, region.id)
    ranges(ctx.session, titan.id, region.id)
    ranges(ctx.session, elk.id, far.id)
    await ctx.session.flush()
    everyone = [wolf, deer, hare, titan, elk]
    change = await derive_links(ctx, everyone)
    assert sorted(change.formed[wolf.id]) == sorted([deer.id, hare.id])
    profile = await ctx.session.get(SpeciesProfileRow, wolf.id)
    assert profile is not None
    profile.barred_prey = [hare.id]
    profile.pinned_prey = [elk.id]
    again = await derive_links(ctx, everyone)
    assert again.broken == 1 and again.formed[wolf.id] == [elk.id]
    hunted = set(
        await ctx.session.scalars(
            select(BondRow.target_node_id).where(BondRow.source_node_id == wolf.id, BondRow.kind == BondKind.HUNTS, BondRow.state == BondState.ACTIVE)
        )
    )
    assert hunted == {deer.id, elk.id}


async def test_an_isolated_herd_in_a_strange_land_becomes_a_subspecies(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "creatures", speciation_chance=100, speciation_min_epochs=1))
    home = await make_region(session, "Lowlands", cosmos.home.id)
    peaks = await make_region(session, "Peaks", cosmos.home.id)
    await land(session, home.id, cosmos.home.id, TerrainKind.PLAIN, 55)
    await land(session, peaks.id, cosmos.home.id, TerrainKind.MOUNTAINS, 10)
    goat = await kind(ctx, cosmos, "Horngoat", home.id, SpeciesSpec(BodyPlan.QUADRUPED, SizeClass.MEDIUM, Diet.HERBIVORE))
    session.add(SpeciesRangeRow(species_entity_id=goat.id, region_entity_id=home.id, abundance=70, since_epoch=0, locked=[]))
    session.add(SpeciesRangeRow(species_entity_id=goat.id, region_entity_id=peaks.id, abundance=30, since_epoch=0, locked=[]))
    await session.flush()
    assert await speciation(ctx) == 1
    child = await session.scalar(select(EntityRow).where(EntityRow.subtype == "highland subspecies"))
    assert child is not None and child.location_id == peaks.id
    shaped = await session.get(SpeciesProfileRow, child.id)
    assert shaped is not None and shaped.size_class is SizeClass.LARGE
    assert await session.get(SpeciesRangeRow, (goat.id, peaks.id)) is None


async def test_a_herd_in_a_like_land_does_not_drift(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "creatures", speciation_chance=100, speciation_min_epochs=1))
    home = await make_region(session, "West Plain", cosmos.home.id)
    other = await make_region(session, "East Plain", cosmos.home.id)
    await land(session, home.id, cosmos.home.id, TerrainKind.PLAIN, 55)
    await land(session, other.id, cosmos.home.id, TerrainKind.PLAIN, 56)
    goat = await kind(ctx, cosmos, "Plaingoat", home.id, SpeciesSpec(BodyPlan.QUADRUPED, SizeClass.MEDIUM, Diet.HERBIVORE))
    ranges(session, goat.id, home.id, other.id)
    await session.flush()
    assert await speciation(ctx) == 0


def test_domestic_kinds_grow_for_work_and_shrink_for_company() -> None:
    rng = SeededRandom.for_epoch(1, 1, "size")
    assert drifted_size(SizeClass.MEDIUM, {SpeciesUse.MOUNT}, rng, 0) is SizeClass.LARGE
    assert drifted_size(SizeClass.MEDIUM, {SpeciesUse.COMPANION}, rng, 0) is SizeClass.SMALL
    assert drifted_size(SizeClass.MEDIUM, {SpeciesUse.FOOD}, rng, 0) is SizeClass.MEDIUM
    assert drifted_size(SizeClass.COLOSSAL, {SpeciesUse.WAR}, rng, 0) is SizeClass.COLOSSAL


def test_overall_abundance_is_the_weighted_total_of_the_ranges() -> None:
    rows = [SpeciesRangeRow(species_entity_id=1, region_entity_id=10, abundance=30), SpeciesRangeRow(species_entity_id=1, region_entity_id=11, abundance=20)]
    assert overall(Rules(), rows, {}) == 50
    assert overall(Rules(), rows, {10: 2.0, 11: 0.5}) == 70
    assert overall(Rules(), [*rows, SpeciesRangeRow(species_entity_id=1, region_entity_id=12, abundance=90)], {}) == 100


async def test_a_carrier_grows_immune_where_its_sickness_rages(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "habitat", immunity_chance=100))
    region = await make_region(session, "Marsh", cosmos.home.id)
    rat = await kind(ctx, cosmos, "Bog Rat", region.id, SpeciesSpec(BodyPlan.QUADRUPED, SizeClass.SMALL, Diet.OMNIVORE))
    pox = await make_entity(session, "Bog Pox", EntityType.DISEASE, DiseaseStats(), world_id=cosmos.home.id)
    ranges(session, rat.id, region.id)
    session.add(SpeciesHostRow(species_entity_id=rat.id, disease_entity_id=pox.id, immune=False, locked=[]))
    session.add(
        OutbreakRow(disease_entity_id=pox.id, region_entity_id=region.id, path=SpreadPath.ORIGIN, status=OutbreakStatus.ACTIVE, severity=40, started_epoch=1)
    )
    await session.flush()
    wilds = await load_wilds(ctx, [rat], set())
    assert await acquire_immunity(ctx, wilds) == 1
    host = await session.get(SpeciesHostRow, (rat.id, pox.id))
    assert host is not None and host.immune


async def test_a_hunt_god_wears_the_head_of_its_peoples_totem(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Antler Wood", cosmos.home.id)
    stag = await kind(ctx, cosmos, "White Stag", region.id, SpeciesSpec(BodyPlan.QUADRUPED, SizeClass.LARGE, Diet.HERBIVORE))
    people = await make_entity(ctx.session, "Stagfolk", EntityType.PEOPLE, PeopleStats(population=100), world_id=cosmos.home.id, location_id=region.id)
    son = await make_son(ctx.session, "Orvik", cosmos.home.id, domains=(Domain.HUNT, Domain.SKY))
    await BondRepository(ctx.session).connect(BondDraft(people.id, son.id, BondKind.WORSHIPS, ctx.epoch, "worship"))
    await found_totem(ctx, people, stag)
    assert await hunt_gods(ctx) == 1
    profile = await ctx.session.get(SpeciesProfileRow, stag.id)
    assert profile is not None and profile.sacred_to_node_id == son.id
    assert CreatureTrait.SACRED_ANIMAL in await EntityRepository(ctx.session).traits(stag.id)
    assert await hunt_gods(ctx) == 0


async def test_a_species_stage_follows_the_herds_kept_of_it(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Pasture", cosmos.home.id)
    ox = await kind(ctx, cosmos, "Wild Ox", region.id, SpeciesSpec(BodyPlan.QUADRUPED, SizeClass.LARGE, Diet.HERBIVORE))
    town = await make_entity(ctx.session, "Oxford", EntityType.SETTLEMENT, SettlementStats(population=200), world_id=cosmos.home.id, location_id=region.id)
    ctx.session.add(HerdRow(community_entity_id=town.id, species_entity_id=ox.id, head=12, stage=DomesticationStage.TAMED, locked=[]))
    await ctx.session.flush()
    assert await stage_from_herds(ctx) == 1
    profile = await ctx.session.get(SpeciesProfileRow, ox.id)
    assert profile is not None and profile.stage is DomesticationStage.TAMED
    herd = await ctx.session.get(HerdRow, (town.id, ox.id))
    assert herd is not None
    await ctx.session.delete(herd)
    await ctx.session.flush()
    assert await stage_from_herds(ctx) == 1 and profile.stage is DomesticationStage.WILD


async def test_the_body_plan_backfill_runs_once(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Deep", cosmos.home.id)
    eel = await kind(ctx, cosmos, "Glass Eel", region.id, SpeciesSpec(BodyPlan.QUADRUPED, SizeClass.SMALL, Diet.CARNIVORE))
    ctx.session.add(
        BodyRow(node_id=eel.id, plan=BodyPlan.SERPENTINE, traits=[], fingers=0, hp_max=0, locked=[], height_class=HeightClass.SHORT, build=BodyBuild.SLIGHT)
    )
    await ctx.session.flush()
    assert await typed_nature_backfill(ctx) == 1
    profile = await ctx.session.get(SpeciesProfileRow, eel.id)
    assert profile is not None and profile.body_plan is BodyPlan.SERPENTINE
    assert await ctx.session.get(AppliedFixupRow, "wilds.typed_nature") is not None
    assert await typed_nature_backfill(ctx) == 0


def test_species_are_no_longer_agents_but_beasts_are() -> None:
    assert EntityType.SPECIES not in AGENT_TYPES and EntityType.BEAST in AGENT_TYPES


def test_beast_abilities_shape_its_reach_harm_waking_taming_and_rest() -> None:
    rules = Rules()
    table = rules.beasts
    stout = BeastProfileRow(endurance=100, perception=100, willpower=100, size_class=SizeClass.COLOSSAL)
    frail = BeastProfileRow(endurance=0, perception=0, willpower=0, size_class=SizeClass.HUGE)
    assert beasts.reach_of(rules, stout) == table.raid_reach + 100 // table.endurance_reach
    assert beasts.reach_of(rules, frail) == table.raid_reach
    assert beasts.wound_harm(rules, stout) < beasts.wound_harm(rules, frail) == table.wound_damage
    assert beasts.wake_chance(rules, stout) > beasts.wake_chance(rules, frail) == table.disturb_chance
    assert beasts.tame_chance(rules, stout) < beasts.tame_chance(rules, frail) == 100
    assert beasts.rest_chance(rules, stout) < beasts.rest_chance(rules, frail) == table.sleep_chance
    assert beasts.size_factor(rules, stout) > beasts.size_factor(rules, frail) == 1.0


async def beast_in(ctx: TickContext, cosmos: Cosmos, region_id: int, **stats: int) -> tuple[EntityRow, BeastProfileRow]:
    beast = await make_entity(ctx.session, "Ashmaw", EntityType.BEAST, BeastStats(**stats), world_id=cosmos.home.id, location_id=region_id)
    row = await beasts.profile_beast(ctx, beast, None)
    row.lair_place_id = region_id
    return beast, row


async def test_a_raid_carries_a_treasure_into_the_hoard_and_the_slayer_takes_it_all(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "beasts", hoard_item_chance=100))
    region = await make_region(session, "Ashlands", cosmos.home.id)
    town = await make_entity(session, "Cinder", EntityType.SETTLEMENT, SettlementStats(population=300), world_id=cosmos.home.id, location_id=region.id)
    crown = await make_entity(session, "Ember Crown", EntityType.ITEM, ItemStats(), world_id=cosmos.home.id, location_id=town.id)
    await BondRepository(session).connect(BondDraft(town.id, crown.id, BondKind.OWNS, ctx.epoch, "regalia"))
    deer = await kind(ctx, cosmos, "Ash Deer", region.id, SpeciesSpec(BodyPlan.QUADRUPED, SizeClass.MEDIUM, Diet.HERBIVORE))
    ranges(session, deer.id, region.id, abundance=40)
    region.stats = region.stats.model_copy(update={"danger": 50})
    beast, row = await beast_in(ctx, cosmos, region.id, strength=90, terror=20)
    await beasts.raid(ctx, beast, row, town)
    assert await beasts.owned_items(ctx, [beast.id]) == [crown.id]
    hero = await make_entity(session, "Ilsa", EntityType.MORTAL, MortalStats(age=30, lifespan=70), world_id=cosmos.home.id, location_id=town.id)
    await BondRepository(session).connect(BondDraft(hero.id, beast.id, BondKind.KILLED, ctx.epoch, "slew the beast"))
    await EntityRepository(session).set_status(beast, EntityStatus.DEAD, ctx.epoch)
    told = await beasts.fall(ctx, beast, row)
    assert "Ilsa" in told
    assert await beasts.owned_items(ctx, [hero.id]) == [crown.id]
    assert hero.title == f"Slayer of {beast.name}"
    deer_range = await session.get(SpeciesRangeRow, (deer.id, region.id))
    assert deer_range is not None and deer_range.abundance == 40 + ctx.rules.beasts.recovery_abundance
    assert region.stats.danger == 50 - ctx.rules.beasts.recovery_danger


async def test_a_slain_kind_of_beast_yields_trophies_to_its_mortal_slayer(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Crags", cosmos.home.id)
    wyrm = await kind(ctx, cosmos, "Wyrm", region.id, SpeciesSpec(BodyPlan.SERPENTINE, SizeClass.HUGE, Diet.CARNIVORE), might=80)
    beast = await make_entity(ctx.session, "Old Wyrm", EntityType.BEAST, BeastStats(strength=90), world_id=cosmos.home.id, location_id=region.id)
    row = await beasts.profile_beast(ctx, beast, wyrm)
    hero = await make_entity(ctx.session, "Bran", EntityType.MORTAL, MortalStats(age=30, lifespan=70), world_id=cosmos.home.id, location_id=region.id)
    assert await beasts.corpse(ctx, beast, row, hero) >= 2
    trophies = await beasts.owned_items(ctx, [hero.id])
    classes = {profile.material for profile in await ctx.session.scalars(select(ItemProfileRow).where(ItemProfileRow.item_entity_id.in_(trophies)))}
    assert "dragonbone" in classes


async def test_a_cowed_town_swears_tribute_and_breaks_it_when_it_cannot_pay(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "beasts", cowed_terror=50))
    region = await make_region(session, "Gorge", cosmos.home.id)
    town = await make_entity(session, "Weir", EntityType.SETTLEMENT, SettlementStats(population=200, defense=5), world_id=cosmos.home.id, location_id=region.id)
    await GoodsLedger(session, ctx.epoch).add(town.id, CommodityKind.LUXURIES, ctx.rules.beasts.tribute_hoard, GoodsFlow.PRODUCTION)
    beast, row = await beast_in(ctx, cosmos, region.id, strength=80, terror=70)
    paid, defiant = await beasts.tribute(ctx, beast, row, [town])
    assert paid == 1 and defiant is None and row.hoard[CommodityKind.LUXURIES.value] == ctx.rules.beasts.tribute_hoard
    clause = await session.scalar(select(TreatyClauseRow).where(TreatyClauseRow.beneficiary_node_id == beast.id, TreatyClauseRow.kind == ClauseKind.TRIBUTE))
    assert clause is not None and clause.obligor_node_id == town.id and clause.last_kept_epoch == ctx.epoch
    paid, defiant = await beasts.tribute(ctx, beast, row, [town])
    assert paid == 0 and defiant is town
    profile = await session.get(TreatyProfileRow, clause.treaty_entity_id)
    assert profile is not None and profile.status is TreatyStatus.BROKEN


async def test_terror_lays_dread_on_the_towns_in_reach(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Hollow", cosmos.home.id)
    town = await make_entity(ctx.session, "Hush", EntityType.SETTLEMENT, SettlementStats(population=200), world_id=cosmos.home.id, location_id=region.id)
    beast, _ = await beast_in(ctx, cosmos, region.id, terror=80)
    await beasts.dread(ctx, beast, [town], quiet=False)
    fear = await ctx.session.scalar(select(MemoryRow).where(MemoryRow.holder_node_id == town.id, MemoryRow.kind == MemoryKind.HARMED_ME))
    assert fear is not None and fear.magnitude == -round(80 * ctx.rules.beasts.terror_insecurity_pct / 100)


async def test_a_tamed_great_beast_is_a_mount_for_war_and_the_roads(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Steppe", cosmos.home.id)
    rider = await make_entity(ctx.session, "Tarik", EntityType.MORTAL, MortalStats(age=30, lifespan=70), world_id=cosmos.home.id, location_id=region.id)
    assert await beasts.mounted_edge(ctx, rider.id) == 1.0 and not await has_tamed_mount(ctx.session, rider.id)
    _, row = await beast_in(ctx, cosmos, region.id, strength=100)
    row.bound_to_node_id, row.temper, row.size_class = rider.id, BeastTemper.TAMED, SizeClass.HUGE
    await ctx.session.flush()
    assert await beasts.mounted_edge(ctx, rider.id) == 1 + ctx.rules.beasts.mount_edge_pct / 100
    assert await has_tamed_mount(ctx.session, rider.id)
    row.size_class = SizeClass.MEDIUM
    await ctx.session.flush()
    assert await beasts.mount_of(ctx, rider.id) is None
