from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.lore import ChronicleRow, LexemeRow
from aerona.db.tables.warfare import WarRow
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityOrigin, EntityStatus, EntityType, LegendCategory
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.war import WarCause, WarStatus
from aerona.domain.enums.world import WorldType
from aerona.domain.models.entity_stats import EventStats, LegendStats, ProphecyStats, SpeciesStats, SpiritStats, TraditionStats
from aerona.engine.lore.legends import profile_of
from aerona.engine.phases.belief_memory import belief_and_memory, event_to_legend, revive_legend
from aerona.engine.phases.births import (
    awaken_species,
    bless_with_child,
    couples_bear_children,
    crown_ruler,
    order_village,
    raise_notable_by_hand,
    single_rule,
    spontaneous_births,
    trigger_ethnogenesis,
)
from aerona.engine.phases.dialects import dialect_divergence
from aerona.engine.phases.language_death import language_death
from aerona.engine.phases.life_seed import life_seed, seed_life
from aerona.engine.phases.migration import famine_migration
from aerona.engine.phases.refugees import order_exodus, refugees
from aerona.engine.phases.ruins import abandon_settlement, abandonment, protect_from_ruin
from aerona.engine.phases.settlements import order_resettlement, resettle_ruin
from aerona.engine.phases.spirits import hauntings, lay_spirit_to_rest, spirits_rest
from aerona.engine.phases.works import commission_work, engine_works, splendor_growth
from aerona.engine.phases.world_age import end_golden_age, proclaim_golden_age, world_age
from aerona.engine.phases.writing import writing_systems
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import has_flag, spoken_language
from aerona.engine.primitives.stats import set_stats, stat
from tests.engine.core.factories import CoreWorld, add_empty_world, bond, entity, knowledge, mortal, settlement, tuned_rules


async def keys(session: AsyncSession) -> list[str | None]:
    return list(await session.scalars(select(ChronicleRow.template_key).order_by(ChronicleRow.id)))


async def test_ruins_fall_and_rise_again(session: AsyncSession, world: CoreWorld) -> None:
    world.cosmos.epoch = 5
    ctx = await manual_context(session, "ruins")
    hamlet = await settlement(session, "Emptyfold", world, world.regions[1], population=10)
    await abandonment(ctx)
    assert hamlet.status is EntityStatus.DEAD
    assert await has_flag(session, hamlet.id, EntityFlag.RUIN)
    rebuilt = await resettle_ruin(ctx, world.regions[1], world.people, 300, "settlers")
    assert rebuilt == hamlet and hamlet.status is EntityStatus.CANON
    assert stat(hamlet, "population") == 300
    assert await has_flag(session, hamlet.id, EntityFlag.REBUILT)
    assert await spoken_language(session, hamlet.id) == world.language
    await abandon_settlement(ctx, hamlet.id)
    assert await order_resettlement(ctx, hamlet.id, world.people.id, 200) == hamlet


async def test_a_sheltered_settlement_never_falls_to_ruin(session: AsyncSession, world: CoreWorld) -> None:
    world.cosmos.epoch = 5
    ctx = await manual_context(session, "ruins")
    hamlet = await settlement(session, "Stillwater", world, world.regions[1], population=10)
    assert await protect_from_ruin(ctx, hamlet.id)
    await abandonment(ctx)
    assert hamlet.status is EntityStatus.CANON
    assert await protect_from_ruin(ctx, hamlet.id, protected=False)
    await abandonment(ctx)
    assert hamlet.status is EntityStatus.DEAD


async def test_famine_drives_migrants_to_greener_lands(session: AsyncSession, world: CoreWorld) -> None:
    set_stats(world.people, prosperity=5)
    ctx = await manual_context(session, "famine", tuned_rules(world_engine={"famine_migration_chance": 100}))
    await famine_migration(ctx)
    moved = await session.scalar(select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT))
    assert moved is not None and moved.location_id == world.regions[1].id
    assert (stat(world.people, "population") or 0) < 6000
    assert "migration.famine" in await keys(session)


async def test_refugees_flee_war_and_the_gods_will(session: AsyncSession, world: CoreWorld) -> None:
    host = await settlement(session, "Greenhold", world, world.regions[1], population=800)
    event = await entity(session, "Battle of Ash", EntityType.EVENT, EventStats(severity=70), world_id=world.world.id, location_id=world.regions[0].id)
    event.engine_kind = EngineKind.BATTLE
    session.add(BondRow(source_node_id=event.id, target_node_id=world.people.id, kind=BondKind.PARTY_TO, role=BondRole.LOSER, epoch=1))
    await session.flush()
    ctx = await manual_context(session, "refugees", tuned_rules(deep_world={"refugee_chance": 100}))
    await refugees(ctx)
    assert (stat(host, "population") or 0) > 800
    exodus = await order_exodus(ctx, world.people.id, 10, host.id)
    assert exodus.shelter == host


async def test_spirits_rest_cross_and_haunt(session: AsyncSession, world: CoreWorld) -> None:
    world.cosmos.epoch = 6
    dead_world, regions = await add_empty_world(session, "Nether")
    dead_world.world_type = WorldType.DEAD
    calm = await entity(
        session, "Calm Shade", EntityType.SPIRIT, SpiritStats(unrest=10), world_id=world.world.id, location_id=world.regions[1].id, origin=EntityOrigin.ENGINE
    )
    town = await settlement(session, "Greenhold", world, world.regions[1], prosperity=50)
    wild = await entity(session, "Howling Shade", EntityType.SPIRIT, SpiritStats(unrest=95), world_id=world.world.id, location_id=world.regions[1].id)
    ctx = await manual_context(session, "spirits", tuned_rules(deep_world={"spirit_rest_chance": 100}, world_engine={"spirit_haunt_chance": 100}))
    await spirits_rest(ctx)
    assert calm.status is EntityStatus.DEAD
    await hauntings(ctx)
    assert (stat(town, "prosperity") or 0) < 50
    assert (await lay_spirit_to_rest(ctx, wild.id)).status is EntityStatus.DEAD
    assert regions


async def test_isolated_settlement_forms_a_dialect(session: AsyncSession, world: CoreWorld) -> None:
    world.cosmos.epoch = 9
    town = await settlement(session, "Farhold", world, world.regions[3])
    await bond(session, town.id, world.language.id, BondKind.SPEAKS)
    ctx = await manual_context(session, "dialects", tuned_rules(world_engine={"dialect_split_chance": 100}))
    await dialect_divergence(ctx)
    dialect = await spoken_language(session, town.id)
    assert dialect is not None and dialect.engine_kind is EngineKind.DIALECT
    assert await BondRepository(session).exists_between(dialect.id, world.language.id, BondKind.DESCENDS_FROM)
    words = list(await session.scalars(select(LexemeRow.word).where(LexemeRow.language_entity_id == dialect.id)))
    assert words


async def test_languages_die_revive_and_gain_scripts(session: AsyncSession, world: CoreWorld) -> None:
    world.cosmos.epoch = 9
    ctx = await manual_context(session, "languages", tuned_rules(deep_world={"script_chance": 100}))
    ink = await knowledge(session, world, "Ink Craft", KnowledgeBranch.WRITING)
    await bond(session, world.people.id, ink.id, BondKind.KNOWS)
    await writing_systems(ctx)
    profile = await session.get(LanguageProfileRow, world.language.id)
    assert profile is not None and profile.writing_system is not None
    for bond_row in await BondRepository(session).incoming(world.language.id, BondKind.SPEAKS):
        await BondRepository(session).deactivate(bond_row, ctx.epoch)
    await language_death(ctx)
    assert await has_flag(session, world.language.id, EntityFlag.DEAD_LANGUAGE)
    assert await has_flag(session, world.language.id, EntityFlag.DECIPHERABLE)
    await bond(session, world.people.id, world.language.id, BondKind.SPEAKS)
    await language_death(ctx)
    assert not await has_flag(session, world.language.id, EntityFlag.DEAD_LANGUAGE)


async def test_births_fill_communities(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(deep_world={"notable_chance": 100, "ruler_chance": 100}, deep_life={"first_village_chance": 100})
    ctx = await manual_context(session, "births", rules)
    await spontaneous_births(ctx)
    mortals = list(await session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL)))
    assert mortals
    settlements = list(await session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT)))
    assert settlements
    texts = await keys(session)
    assert "births.ruler" in texts and "births.village" in texts


async def test_manual_births(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "manual_births")
    first = await mortal(session, "Ana", world, world.regions[0].id)
    second = await mortal(session, "Bo", world, world.regions[0].id)
    child = await bless_with_child(ctx, first.id, second.id)
    assert await BondRepository(session).exists_between(first.id, child.id, BondKind.PARENT_OF)
    notable = await raise_notable_by_hand(ctx, world.people.id)
    assert notable.mortal_role is not None
    ruler = await crown_ruler(ctx, world.people.id)
    assert await BondRepository(session).exists_between(ruler.id, world.people.id, BondKind.RULES)
    village = await order_village(ctx, world.people.id)
    assert village.entity_type is EntityType.SETTLEMENT
    town = await settlement(session, "Farhold", world, world.regions[3], population=5000)
    await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
    people = await trigger_ethnogenesis(ctx, town.id)
    assert people.entity_type is EntityType.PEOPLE
    smart = await entity(
        session, "Owlkin", EntityType.SPECIES, SpeciesStats(intelligence=90, strength=30), world_id=world.world.id, location_id=world.regions[2].id
    )
    uplifted = await awaken_species(ctx, smart.id)
    assert await has_flag(session, smart.id, EntityFlag.SPECIES_BECAME_PEOPLE)
    assert uplifted.entity_type is EntityType.PEOPLE


async def test_couples_and_single_rule(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "couples", tuned_rules(world_engine={"birth_chance": 100}, fertility={"stillbirth_pct": 0.0}))
    first = await mortal(session, "Ana", world, world.regions[0].id, age=25)
    second = await mortal(session, "Bo", world, world.regions[0].id, age=25)
    await bond(session, first.id, second.id, BondKind.SPOUSE_OF)
    await couples_bear_children(ctx)
    assert "births.child" in await keys(session)
    town = await settlement(session, "Brookhold", world, world.regions[0])
    session.add_all(
        [
            BondRow(source_node_id=first.id, target_node_id=town.id, kind=BondKind.RULES, epoch=1),
            BondRow(source_node_id=second.id, target_node_id=town.id, kind=BondKind.RULES, epoch=1),
        ]
    )
    await session.flush()
    assert await single_rule(ctx) == 1


async def test_empty_worlds_come_alive(session: AsyncSession, world: CoreWorld) -> None:
    world.cosmos.epoch = 6
    empty, regions = await add_empty_world(session)
    ctx = await manual_context(session, "life")
    await life_seed(ctx)
    natives = list(await session.scalars(select(EntityRow).where(EntityRow.world_id == empty.id, EntityRow.entity_type == EntityType.PEOPLE)))
    assert natives and await has_flag(session, natives[0].id, EntityFlag.NATIVE)
    species = await seed_life(ctx, empty.id, people=False)
    assert species.entity_type is EntityType.SPECIES and species.location_id in {region.id for region in regions}


async def test_works_rise_and_grow_in_splendor(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Brookhold", world, world.regions[0], population=5000, prosperity=80, defense=20)
    stone = await knowledge(session, world, "Stone Art", KnowledgeBranch.ARCHITECTURE)
    await bond(session, town.id, stone.id, BondKind.KNOWS)
    await bond(session, town.id, world.son.id, BondKind.WORSHIPS)
    ctx = await manual_context(session, "works", tuned_rules(deep_world={"structure_chance": 100}))
    await engine_works(ctx)
    built = list(await session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.STRUCTURE)))
    assert built
    before = stat(built[0], "splendor") or 0
    await splendor_growth(ctx)
    assert (stat(built[0], "splendor") or 0) > before
    assert (await commission_work(ctx, town.id, EngineKind.LIBRARY)).engine_kind is EngineKind.LIBRARY


async def test_belief_and_memory(session: AsyncSession, world: CoreWorld) -> None:
    world.cosmos.epoch = 30
    rules = tuned_rules(deep_world={"manifestation_chance": 100, "legendization_chance": 100, "fairy_tale_chance": 100})
    ctx = await manual_context(session, "memory", rules)
    spring = await entity(session, "The Singing Spring", EntityType.LEGEND, LegendStats(spread=95), world_id=world.world.id)
    await bond(session, spring.id, world.regions[1].id, BondKind.TELLS_OF)
    await bond(session, world.people.id, spring.id, BondKind.TELLS_OF)
    (await profile_of(ctx, spring)).credence = 90
    faded = await entity(session, "Old Dust", EntityType.TRADITION, TraditionStats(spread=5), world_id=world.world.id)
    battle = await entity(session, "Red Field", EntityType.EVENT, EventStats(severity=90), world_id=world.world.id, location_id=world.regions[0].id)
    prophecy = await entity(session, "The Long Wait", EntityType.PROPHECY, ProphecyStats(certainty=50), world_id=world.world.id)
    whisper = await entity(session, "Small Tale", EntityType.LEGEND, LegendStats(spread=10), world_id=world.world.id)
    await belief_and_memory(ctx)
    assert await has_flag(session, spring.id, EntityFlag.MANIFESTED)
    assert spring.legend_category is LegendCategory.RESOURCE
    assert faded.status is EntityStatus.DEAD
    assert prophecy.status is EntityStatus.DEAD
    assert await BondRepository(session).incoming(battle.id, BondKind.TELLS_OF)
    assert await has_flag(session, whisper.id, EntityFlag.FAIRY_TALE)
    assert (await revive_legend(ctx, whisper.id)).status is EntityStatus.CANON
    other = await entity(session, "Black Flood", EntityType.EVENT, EventStats(severity=10), world_id=world.world.id, location_id=world.regions[0].id)
    assert (await event_to_legend(ctx, other.id)).entity_type is EntityType.LEGEND


async def test_world_age_and_golden_ages(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "age", tuned_rules(deep_world={"golden_age_prosperity": 10}, deep_life={"golden_age_min_world_age": 0}))
    result = await world_age(ctx, 10)
    assert result.relief == ctx.rules.deep_world.era_turn_apocalypse_push
    assert result.golden_worlds == 1
    assert await has_flag(session, world.people.id, EntityFlag.GOLDEN_AGE)
    session.add(WarRow(event_entity_id=world.species.id, world_id=world.world.id, status=WarStatus.ONGOING, cause=WarCause.HOSTILITY, started_epoch=1))
    await session.flush()
    again = await world_age(ctx, 11)
    assert again.golden_worlds == 0
    assert not await has_flag(session, world.people.id, EntityFlag.GOLDEN_AGE)
    assert await proclaim_golden_age(ctx, world.world.id) == 1
    assert await end_golden_age(ctx, world.world.id)
    assert isinstance(await session.get(WorldRow, world.world.id), WorldRow)
