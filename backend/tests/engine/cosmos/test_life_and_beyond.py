from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import LegendaryQuestRow, ThreadRow
from aerona.db.tables.society import ArchiveHoldingRow, SoulRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import LegendaryQuestKind, LegendaryQuestOutcome
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.society import CreatureTrait, KnowledgeBranch
from aerona.domain.enums.world import StarType, WorldType
from aerona.domain.models.entity_stats import KnowledgeStats, MortalStats, PeopleStats, SpeciesStats, SpiritStats, StructureStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.fauna import merge_species, stowaway
from aerona.engine.cosmos.quests import legendary_quests, open_quest, settle_quest
from aerona.engine.phases.afterlife import archive_burned, cosmic_court, mirror_worlds, pursuit_of_immortality, soul_bind, soul_descent
from aerona.engine.phases.creatures import _mutation_chance, danger_reversion, predation_pressure, predator_bonds, species_mutations, starving_predators
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region, make_son, make_world, teach, tick, tuned


async def test_mutation_and_chimera(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "creatures", mutation_cursed_bonus_pct=100))
    beast = await make_entity(
        session, "Graveling", EntityType.SPECIES, SpeciesStats(strength=50, danger=40), world_id=cosmos.home.id, flags=[EntityFlag.CURSED]
    )
    assert await species_mutations(ctx) == 1
    assert EntityFlag.MUTATED in await EntityRepository(session).flags(beast.id)
    other = await make_entity(session, "Owlstag", EntityType.SPECIES, SpeciesStats(strength=30, danger=20), world_id=cosmos.home.id)
    chimera = await merge_species(ctx, beast, other)
    assert chimera.engine_kind is EngineKind.CHIMERA and EntityFlag.CHIMERA in await EntityRepository(session).flags(chimera.id)
    assert await BondRepository(session).exists_between(chimera.id, beast.id, BondKind.DESCENDS_FROM)


async def test_mutation_chance_adds_the_might_term(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "creatures", mutation_might_bonus_pct=100))
    plain = await make_entity(session, "Plainback", EntityType.SPECIES, SpeciesStats(strength=50, danger=40), world_id=cosmos.home.id)
    assert await _mutation_chance(ctx, plain, {}, set()) == 0
    mighty = await make_entity(session, "Titanback", EntityType.SPECIES, SpeciesStats(strength=50, danger=40, might=60), world_id=cosmos.home.id)
    assert await _mutation_chance(ctx, mighty, {}, set()) == 1.0
    assert await species_mutations(ctx) == 1
    assert EntityFlag.MUTATED in await EntityRepository(session).flags(mighty.id)
    assert EntityFlag.MUTATED not in await EntityRepository(session).flags(plain.id)


async def test_predators_hunt_starve_and_revert(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "creatures", prey_depletion_chance=100))
    region = await make_region(session, "Wilds", cosmos.home.id)
    wolf = await make_entity(session, "Duskwolf", EntityType.SPECIES, SpeciesStats(strength=80, danger=90), world_id=cosmos.home.id, location_id=region.id)
    deer = await make_entity(
        session, "Glimdeer", EntityType.SPECIES, SpeciesStats(strength=20, danger=10), world_id=cosmos.home.id, location_id=region.id, power=2
    )
    session.add_all([SpeciesRangeRow(species_entity_id=kind.id, region_entity_id=region.id, abundance=60) for kind in (wolf, deer)])
    await session.flush()
    assert await predator_bonds(ctx) == 1
    assert await predation_pressure(ctx) == 1 and deer.status is EntityStatus.DEAD
    assert await starving_predators(ctx) == 1
    assert wolf.stats.danger == 100
    await danger_reversion(ctx)
    assert wolf.stats.danger is not None and wolf.stats.danger < 100


async def test_stowaway_crosses_worlds(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "creatures", stowaway_chance=100))
    await make_entity(session, "Ratling", EntityType.SPECIES, SpeciesStats(danger=10), world_id=cosmos.home.id)
    other = await make_world(session, "Velmor")
    landing = await make_region(session, "Port", other.id)
    carried = await stowaway(ctx, cosmos.home.id, landing)
    assert carried is not None and carried.world_id == other.id
    assert EntityFlag.INVASIVE in await EntityRepository(session).flags(carried.id)


async def test_soul_binding_makes_a_golem(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Hills", cosmos.home.id)
    soul = await make_entity(ctx.session, "Shade", EntityType.SPIRIT, SpiritStats(), world_id=cosmos.home.id, location_id=region.id)
    work = await make_entity(ctx.session, "Stone Gate", EntityType.STRUCTURE, StructureStats(), world_id=cosmos.home.id, location_id=region.id, power=6)
    golem = await soul_bind(ctx, soul.id, work.id, "Aeron")
    assert golem.engine_kind is EngineKind.GOLEM and soul.status is EntityStatus.DEAD
    assert CreatureTrait.STONESKIN in await EntityRepository(ctx.session).traits(golem.id)


async def test_souls_descend_to_their_own_world(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "beyond", soul_descent_chance=100))
    underworld = await make_region(session, "Below", cosmos.home.id)
    underworld.is_underworld = True
    stranger_world = await make_world(session, "Nethis", WorldType.DEAD)
    await make_region(session, "Ash Shore", stranger_world.id)
    dead = await make_entity(session, "Orrin", EntityType.MORTAL, MortalStats(age=60, lifespan=70), world_id=cosmos.home.id)
    await EntityRepository(session).set_status(dead, EntityStatus.DEAD, ctx.epoch)
    assert await soul_descent(ctx) == 1
    record = await session.scalar(select(SoulRow))
    assert record is not None and record.realm_entity_id == underworld.id and record.origin_world_id == cosmos.home.id


async def test_mirror_world_births_inverses(ctx: TickContext, cosmos: Cosmos) -> None:
    mirror = await make_world(ctx.session, "Glassa", WorldType.MIRROR)
    mirror.mirror_twin_id = cosmos.home.id
    await make_region(ctx.session, "Silver", mirror.id)
    dead = await make_entity(ctx.session, "Orrin", EntityType.MORTAL, MortalStats(strength=70, age=60, lifespan=70), world_id=cosmos.home.id)
    await EntityRepository(ctx.session).set_status(dead, EntityStatus.DEAD, ctx.epoch)
    assert await mirror_worlds(ctx) == 1
    born = await ctx.session.scalar(select(EntityRow).where(EntityRow.engine_kind == EngineKind.MIRROR_BIRTH))
    assert born is not None and born.stats.strength == 30 and born.world_id == mirror.id


async def test_legendary_quest_lifecycle(ctx: TickContext, cosmos: Cosmos) -> None:
    cosmos.star.star_type = StarType.DEAD_STAR
    quest = await open_quest(ctx, LegendaryQuestKind.DEAD_STAR, "Aeron", ActorKind.CREATOR)
    assert quest.target_star_id == cosmos.star.id
    cosmos.star.star_type = StarType.REBORN_STAR
    essence = cosmos.creator.essence
    await legendary_quests(ctx)
    assert quest.outcome is LegendaryQuestOutcome.COMPLETED
    assert cosmos.creator.essence == essence + ctx.rules.beyond.expedition_reward_essence
    cosmos.star.star_type = StarType.BLACK_SUN
    failing = await open_quest(ctx, LegendaryQuestKind.DEAD_STAR, "Fate", ActorKind.FATE)
    late = tick(ctx.session, ctx.rules, epoch=failing.deadline_epoch)
    thread = await ctx.session.get(ThreadRow, failing.thread_id)
    assert thread is not None
    assert await settle_quest(late, failing, thread) is LegendaryQuestOutcome.FAILED
    cosmos_row = await CosmosRepository(ctx.session).require_cosmos()
    assert cosmos_row.doom_clock == ctx.rules.beyond.expedition_fail_apocalypse
    assert len(list(await ctx.session.scalars(select(LegendaryQuestRow)))) == 2


async def test_archive_burns_only_what_it_held(ctx: TickContext, cosmos: Cosmos) -> None:
    rules = tuned(ctx.rules, "beyond", archive_burn_loss_pct=100)
    burn = tick(ctx.session, rules)
    archive = await make_entity(
        ctx.session, "Cosmic Archive", EntityType.STRUCTURE, StructureStats(), world_id=cosmos.home.id, engine_kind=EngineKind.COSMIC_ARCHIVE
    )
    reader = await make_entity(ctx.session, "Scribes", EntityType.PEOPLE, PeopleStats(population=500), world_id=cosmos.home.id)
    held = await make_entity(
        ctx.session, "Star Charts", EntityType.KNOWLEDGE, KnowledgeStats(level=2), world_id=cosmos.home.id, knowledge_branch=KnowledgeBranch.ASTRONOMY
    )
    await BondRepository(ctx.session).connect(BondDraft(reader.id, held.id, BondKind.KNOWS, 1))
    own = await teach(ctx.session, reader, KnowledgeBranch.WRITING)
    ctx.session.add(ArchiveHoldingRow(archive_entity_id=archive.id, knowledge_entity_id=held.id, reader_entity_id=reader.id, epoch=1))
    await EntityRepository(ctx.session).set_status(archive, EntityStatus.DESTROYED, ctx.epoch)
    assert await archive_burned(burn) == 1
    bonds = BondRepository(ctx.session)
    assert not await bonds.exists_between(reader.id, held.id, BondKind.KNOWS)
    assert await bonds.exists_between(reader.id, own.id, BondKind.KNOWS)


async def test_cosmic_court_and_immortality(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "beyond", immortality_chance=100))
    await make_world(session, "Velmor")
    traitor = await make_entity(session, "Tarn", EntityType.PEOPLE, PeopleStats(population=500), world_id=cosmos.home.id)
    victim = await make_entity(session, "Vesk", EntityType.PEOPLE, PeopleStats(population=500), world_id=cosmos.home.id)
    text = await cosmic_court(ctx, traitor.id, victim.id)
    assert text is not None and EntityFlag.OATHBREAKER in await EntityRepository(session).flags(traitor.id)
    son = await make_son(session, "Velan", cosmos.home.id)
    sage = await make_entity(session, "Iska", EntityType.MORTAL, MortalStats(intellect=90, charisma=60, age=40, lifespan=80), world_id=cosmos.home.id)
    await teach(session, sage, KnowledgeBranch.IMMORTALITY)
    assert await pursuit_of_immortality(ctx) == 1
    assert EntityFlag.IMMORTAL in await EntityRepository(session).flags(sage.id)
    assert son.wrath == 20 + rules.beyond.immortality_son_wrath
