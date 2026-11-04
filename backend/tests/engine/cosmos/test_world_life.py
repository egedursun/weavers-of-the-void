import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import JourneyRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.society import CreatureTrait, KnowledgeBranch
from aerona.domain.enums.travel import JourneyIntent, JourneyStatus
from aerona.domain.enums.world import WorldType
from aerona.domain.models.entity_stats import PeopleStats, SettlementStats, SpeciesStats, SpiritStats
from aerona.engine.phases.afterlife import cosmic_plague, planet_acts, planet_worship, void_storm
from aerona.engine.phases.creatures import creature_migration, creature_rebellion, order_feeding, spare_soul, speciation
from aerona.engine.phases.exploration import exploration_summary
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region, make_route, make_son, make_world, teach, tick, tuned


async def test_creature_rebellion_and_speciation(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "creatures", creature_revolt_chance=100, speciation_chance=100))
    son = await make_son(session, "Velan", cosmos.home.id)
    region = await make_region(session, "Wilds", cosmos.home.id)
    beast = await make_entity(
        session,
        "Clevermaw",
        EntityType.SPECIES,
        SpeciesStats(intelligence=80, danger=80, strength=50),
        world_id=cosmos.home.id,
        location_id=region.id,
        creator_son_id=son.id,
    )
    assert await creature_rebellion(ctx) == 1
    assert son.existence == 60 - rules.creatures.creature_revolt_son_existence_loss
    await BondRepository(session).connect(BondDraft(beast.id, region.id, BondKind.LIVES_IN, 1))
    assert await speciation(ctx) == 1
    child = await session.scalar(select(EntityRow).where(EntityRow.subtype.like("%subspecies")))
    assert child is not None and await BondRepository(session).exists_between(child.id, beast.id, BondKind.DESCENDS_FROM)


async def test_creature_migration_without_a_map_stays_home(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "creatures", creature_migration_chance=100))
    region = await make_region(session, "Wilds", cosmos.home.id)
    await make_entity(session, "Duskwolf", EntityType.SPECIES, SpeciesStats(danger=90), world_id=cosmos.home.id, location_id=region.id)
    assert await creature_migration(ctx) == 0


async def test_living_planet_acts(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "beyond", planet_punish_chance=100, planet_worship_chance=100))
    planet = await make_world(session, "Carnis", WorldType.LIVING)
    region = await make_region(session, "Skin Plain", planet.id)
    polluter = await make_entity(session, "Ashfolk", EntityType.SETTLEMENT, SettlementStats(population=5000), world_id=planet.id, location_id=region.id)
    await teach(session, polluter, KnowledgeBranch.FORBIDDEN)
    text = await planet_acts(ctx, planet)
    assert text is not None and "shook" in text and polluter.stats.population is not None and polluter.stats.population < 5000
    godless = await make_entity(session, "Wanderers", EntityType.PEOPLE, PeopleStats(population=500), world_id=planet.id)
    assert await planet_worship(ctx, planet) >= 1
    assert EntityFlag.WORSHIPS_PLANET in await EntityRepository(session).flags(godless.id) or EntityFlag.WORSHIPS_PLANET in await EntityRepository(
        session
    ).flags(polluter.id)


async def test_plague_and_void_storm(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "beyond", cosmic_plague_chance=100, void_storm_chance=100, storm_loss_chance=0))
    other = await make_world(session, "Velmor")
    colony = await make_entity(session, "Farhold", EntityType.SETTLEMENT, SettlementStats(population=1000), world_id=other.id)
    people = await make_entity(session, "Tarn", EntityType.PEOPLE, PeopleStats(population=8000), world_id=cosmos.home.id)
    route = await make_route(session, cosmos.home.id, other.id)
    session.add(
        JourneyRow(
            traveller_entity_id=people.id,
            route_id=route.id,
            origin_world_id=cosmos.home.id,
            destination_world_id=other.id,
            intent=JourneyIntent.COLONY,
            epochs_left=0,
            status=JourneyStatus.ARRIVED,
            start_epoch=ctx.epoch,
            result_entity_id=colony.id,
        )
    )
    await session.flush()
    assert await cosmic_plague(ctx) == 1
    assert EntityFlag.COSMIC_PLAGUE in await EntityRepository(session).flags(colony.id)
    assert await void_storm(ctx) is not None and not route.active


async def test_exploration_summary(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    summary = await exploration_summary(session, rules)
    assert [item.world.id for item in summary.worlds] == [cosmos.home.id]
    assert summary.lands_cap == rules.exploration.per_epoch_cap


async def test_the_creator_orders_a_soul_eater_to_feed_or_spares_a_soul(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    region = await make_region(session, "Hollow Fen", cosmos.home.id)
    eater = await make_entity(
        session, "Gloomjaw", EntityType.SPECIES, SpeciesStats(danger=60), world_id=cosmos.home.id, location_id=region.id, traits=[CreatureTrait.SOUL_EATER]
    )
    kept = await make_entity(session, "Kept Shade", EntityType.SPIRIT, SpiritStats(), world_id=cosmos.home.id, location_id=region.id)
    lost = await make_entity(session, "Lost Shade", EntityType.SPIRIT, SpiritStats(), world_id=cosmos.home.id, location_id=region.id)
    assert await spare_soul(session, rules, kept.id)
    eaten = await order_feeding(session, rules, eater.id)
    assert eaten.id == lost.id and lost.status is EntityStatus.DEAD
    with pytest.raises(ValidationFailedError):
        await order_feeding(session, rules, eater.id)
    assert kept.status is EntityStatus.CANON
