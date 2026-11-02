from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.society import CreatureTrait, KnowledgeBranch
from aerona.domain.models.entity_stats import SpeciesStats, SpiritStats
from aerona.engine.cosmos.fauna import weave_chimera
from aerona.engine.cosmos.sanity import sanity_of
from aerona.engine.phases.creatures import (
    chimera_escapes,
    creature_migration,
    hybridize,
    invasive_pressure,
    megafauna,
    trait_effects,
    weave_spontaneously,
)
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import has_flag
from aerona.engine.primitives.stats import stat
from tests.engine.core.factories import CoreWorld, add_flag, bond, entity, knowledge, mortal, settlement, tuned_rules


async def keys(session: AsyncSession) -> list[str | None]:
    return list(await session.scalars(select(ChronicleRow.template_key).order_by(ChronicleRow.id)))


async def beast(session: AsyncSession, world: CoreWorld, name: str, *, power: int = 3, **stats: int) -> EntityRow:
    values = {"hp": 80, "strength": 40, "agility": 40, "intelligence": 20, "danger": 30} | stats
    return await entity(session, name, EntityType.SPECIES, SpeciesStats(**values), world_id=world.world.id, location_id=world.regions[2].id, power_level=power)


async def test_radiant_species_calms_and_greens_its_region(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "radiant")
    creatures = ctx.rules.creatures
    await EntityRepository(session).add_trait(world.species.id, CreatureTrait.RADIANT)
    region = world.regions[2]
    danger, fertility = stat(region, "danger"), stat(region, "fertility")
    await trait_effects(ctx, world.species)
    assert stat(region, "danger") == (danger or 0) - creatures.radiant_danger_drop
    assert stat(region, "fertility") == (fertility or 0) + creatures.radiant_fertility_gain


async def test_soul_eater_swallows_a_spirit_with_certain_chance(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "eater", tuned_rules(creatures={"soul_eater_chance": 100}))
    await EntityRepository(session).add_trait(world.species.id, CreatureTrait.SOUL_EATER)
    shade = await entity(session, "Pale Shade", EntityType.SPIRIT, SpiritStats(), world_id=world.world.id, location_id=world.regions[2].id)
    await trait_effects(ctx, world.species)
    assert shade.status is EntityStatus.DEAD
    assert "creatures.soul_eaten" in await keys(session)


async def test_soul_eater_leaves_spirits_alone_when_chance_is_zero(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "eater", tuned_rules(creatures={"soul_eater_chance": 0}))
    await EntityRepository(session).add_trait(world.species.id, CreatureTrait.SOUL_EATER)
    shade = await entity(session, "Pale Shade", EntityType.SPIRIT, SpiritStats(), world_id=world.world.id, location_id=world.regions[2].id)
    await trait_effects(ctx, world.species)
    assert shade.status is EntityStatus.CANON
    assert "creatures.soul_eaten" not in await keys(session)


async def test_mind_reader_erodes_the_sanity_of_those_nearby(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "mind")
    creatures = ctx.rules.creatures
    await EntityRepository(session).add_trait(world.species.id, CreatureTrait.MIND_READER)
    neighbour = await mortal(session, "Dorn", world, world.regions[2].id)
    before = sanity_of(ctx.rules, neighbour)
    await trait_effects(ctx, world.species)
    assert sanity_of(ctx.rules, neighbour) == before - creatures.mind_reader_sanity_loss


async def test_fissiparous_species_grows_more_dangerous(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "fission", tuned_rules(creatures={"fission_chance": 100}))
    await EntityRepository(session).add_trait(world.species.id, CreatureTrait.FISSIPAROUS)
    await trait_effects(ctx, world.species)
    assert stat(world.species, "danger") == 30 + ctx.rules.creatures.fission_danger_gain


async def test_species_sharing_a_land_hybridize_but_the_same_pair_never_twice(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "hybrid", tuned_rules(creatures={"hybrid_chance": 100}))
    other = await beast(session, world, "Marshstrider")
    hybrid = await hybridize(ctx)
    assert hybrid is not None and hybrid.subtype == "hybrid"
    repository = BondRepository(session)
    assert await repository.exists_between(hybrid.id, world.species.id, BondKind.DESCENDS_FROM)
    assert await repository.exists_between(hybrid.id, other.id, BondKind.DESCENDS_FROM)
    assert await has_flag(session, hybrid.id, EntityFlag.CHIMERA)
    assert "creatures.hybrid" in await keys(session)
    again = await hybridize(ctx)
    assert again is None or not (
        await repository.exists_between(again.id, world.species.id, BondKind.DESCENDS_FROM)
        and await repository.exists_between(again.id, other.id, BondKind.DESCENDS_FROM)
    )


async def test_species_in_different_lands_do_not_hybridize(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "hybrid", tuned_rules(creatures={"hybrid_chance": 100}))
    await entity(
        session,
        "Hillgrazer",
        EntityType.SPECIES,
        SpeciesStats(hp=60, strength=20, agility=20, intelligence=10, danger=10),
        world_id=world.world.id,
        location_id=world.regions[0].id,
    )
    assert await hybridize(ctx) is None
    assert "creatures.hybrid" not in await keys(session)


async def biomancer(session: AsyncSession, world: CoreWorld, location_id: int) -> EntityRow:
    weaver = await mortal(session, "Orsa", world, location_id, intellect=90)
    lore = await knowledge(session, world, "Flesh Craft", KnowledgeBranch.BIOMANCY)
    await bond(session, weaver.id, lore.id, BondKind.KNOWS)
    return weaver


async def test_biomancer_weaves_a_chimera_on_its_own(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "weave", tuned_rules(creatures={"chimera_weave_chance": 100}))
    await beast(session, world, "Marshstrider")
    weaver = await biomancer(session, world, world.regions[2].id)
    chimera = await weave_spontaneously(ctx)
    assert chimera is not None and await has_flag(session, chimera.id, EntityFlag.CHIMERA)
    repository = BondRepository(session)
    assert await repository.exists_between(weaver.id, chimera.id, BondKind.PRODUCED)
    assert await repository.exists_between(weaver.id, chimera.id, BondKind.TAMED)
    kinds = list(await session.scalars(select(ChronicleRow.kind).where(ChronicleRow.template_key == "creatures.chimera_woven")))
    assert kinds == [ChronicleKind.CHIMERA]


async def test_no_spontaneous_weaving_without_biomancy_or_when_chance_is_zero(session: AsyncSession, world: CoreWorld) -> None:
    await beast(session, world, "Marshstrider")
    await mortal(session, "Plain", world, world.regions[2].id)
    certain = await manual_context(session, "weave", tuned_rules(creatures={"chimera_weave_chance": 100}))
    assert await weave_spontaneously(certain) is None
    await biomancer(session, world, world.regions[2].id)
    never = await manual_context(session, "weave", tuned_rules(creatures={"chimera_weave_chance": 0}))
    assert await weave_spontaneously(never) is None
    assert "creatures.chimera_woven" not in await keys(session)


async def test_woven_chimera_escapes_and_turns_on_its_weavers(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "escape", tuned_rules(creatures={"chimera_escape_divisor": 1}))
    other = await beast(session, world, "Marshstrider")
    weaver = await settlement(session, "Weavers Rest", world, world.regions[0], population=1000)
    chimera = await weave_chimera(ctx, world.species, other, weaver=weaver)
    assert await chimera_escapes(ctx) == 1
    assert await has_flag(session, chimera.id, EntityFlag.ESCAPED)
    assert await BondRepository(session).exists_between(chimera.id, weaver.id, BondKind.HUNTS)
    assert stat(weaver, "population") == 1000 * (100 - ctx.rules.creatures.chimera_escape_population_loss_pct) // 100
    assert "creatures.chimera_escaped" in await keys(session)
    assert await chimera_escapes(ctx) == 0


async def test_chimera_without_a_weaver_never_escapes(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "escape", tuned_rules(creatures={"chimera_escape_divisor": 1}))
    other = await beast(session, world, "Marshstrider")
    await weave_chimera(ctx, world.species, other)
    assert await chimera_escapes(ctx) == 0


async def test_mighty_species_becomes_megafauna_and_leaves_a_trail(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "mega", tuned_rules(creatures={"megafauna_trace_chance": 100}))
    giant = await beast(session, world, "Worldbreaker", power=ctx.rules.creatures.megafauna_min_power)
    trails = await megafauna(ctx)
    assert trails == 1
    assert await has_flag(session, giant.id, EntityFlag.MEGAFAUNA)
    assert not await has_flag(session, world.species.id, EntityFlag.MEGAFAUNA)
    trail = await session.scalar(select(EntityRow).where(EntityRow.subtype == "trail resource"))
    assert trail is not None and trail.location_id == giant.location_id
    recorded = await keys(session)
    assert "creatures.megafauna" in recorded and "creatures.megafauna_trail" in recorded


async def test_invasive_species_drains_regional_fertility(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "invasive")
    await add_flag(session, world.species.id, EntityFlag.INVASIVE)
    region = world.regions[2]
    before = stat(region, "fertility") or 0
    await invasive_pressure(ctx)
    assert stat(region, "fertility") == before - ctx.rules.creatures.invasive_fertility_loss


async def test_dangerous_species_spreads_into_a_neighbouring_region(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "migration", tuned_rules(creatures={"creature_migration_chance": 100, "creature_migration_min_danger": 10}))
    assert await creature_migration(ctx) == 1
    homes = await BondRepository(session).outgoing(world.species.id, BondKind.LIVES_IN)
    assert len(homes) == 1 and homes[0].target_node_id in {world.regions[1].id, world.regions[3].id}
    assert "creatures.migration" in await keys(session)
