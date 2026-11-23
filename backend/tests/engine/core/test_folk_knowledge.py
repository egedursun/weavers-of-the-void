from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.cosmography import CelestialReadingRow
from aerona.db.tables.crafts import NumberSystemRow
from aerona.db.tables.disease import DiseaseProfileRow
from aerona.db.tables.ecology import SpeciesProductRow, SpeciesProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folk_knowledge import FolkClassRow, FolkKnowledgeRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.mind import CultureValueRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.cosmography import OmenReading
from aerona.domain.enums.disease import ClimateWarmth
from aerona.domain.enums.ecology import SpeciesClass
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.folk_knowledge import FolkDomain, FolkTaking, LoreHolders, LoreTransmission
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.models.entity_stats import CelestialStats, DiseaseStats, PeopleStats, SpeciesStats
from aerona.engine.context import TickContext
from aerona.engine.folk_knowledge.factor import folk_factor
from aerona.engine.folk_knowledge.lore import FolkTally, keep_folk_knowledge, watch_the_heavens
from aerona.engine.folk_knowledge.seed import seed_folk_knowledge
from aerona.engine.primitives.stats import stat
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules


def tuned(ctx: TickContext, **values: int) -> TickContext:
    return replace(ctx, environment=replace(ctx.environment, rules=tuned_rules(folk_knowledge=values)))


async def home_town(session: AsyncSession, world: CoreWorld, people: EntityRow, name: str = "Ardun") -> EntityRow:
    town = await settlement(session, name, world, world.regions[0])
    await bond(session, town.id, people.id, BondKind.DESCENDS_FROM)
    session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, unrest=20, locked=[], foreigners={}))
    await session.flush()
    return town


async def knowing(session: AsyncSession, people: EntityRow, domain: FolkDomain, **values: object) -> FolkKnowledgeRow:
    row = FolkKnowledgeRow(people_entity_id=people.id, domain=domain, locked=[], **values)
    session.add(row)
    await session.flush()
    return row


async def poison_plant(session: AsyncSession, world: CoreWorld) -> EntityRow:
    weed = await entity(session, "Bitter Sedge", EntityType.SPECIES, SpeciesStats(), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(SpeciesProfileRow(species_entity_id=weed.id, species_class=SpeciesClass.PLANT))
    session.add(SpeciesProductRow(species_entity_id=weed.id, product="sap", commodity=CommodityKind.POISON))
    await session.flush()
    return weed


async def kinds_of(session: AsyncSession) -> list[str]:
    return list(await session.scalars(select(IncidentRow.kind).where(IncidentRow.kind.startswith("folk.")).order_by(IncidentRow.id)))


async def test_every_people_knows_each_domain_from_its_values_and_reads_numbers_by_its_superstition(
    session: AsyncSession, world: CoreWorld, ctx: TickContext
) -> None:
    session.add_all(
        [
            CultureValueRow(entity_id=world.people.id, axis=ValueAxis.NATURE, value=80),
            CultureValueRow(entity_id=world.people.id, axis=ValueAxis.SUPERSTITION, value=80),
            CultureValueRow(entity_id=world.people.id, axis=ValueAxis.TRADITION, value=90),
        ]
    )
    session.add(NumberSystemRow(people_entity_id=world.people.id, base=10, locked=[]))
    await session.flush()
    assert await seed_folk_knowledge(ctx) >= 1
    rows = {row.domain: row for row in await session.scalars(select(FolkKnowledgeRow).where(FolkKnowledgeRow.people_entity_id == world.people.id))}
    assert set(rows) == set(FolkDomain)
    assert rows[FolkDomain.PLANTS].depth == 90 and rows[FolkDomain.PLANTS].holders is LoreHolders.ELDERS
    system = await session.get(NumberSystemRow, world.people.id)
    assert system is not None and len(system.numerology) == 3
    assert all(0 < int(number) < 10 for number in system.numerology)


async def test_a_people_names_a_poisonous_plant_wrongly_and_it_hurts_one_of_them(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town = await home_town(session, world, world.people)
    victim = await mortal(session, "Ilda", world, town.id)
    weed = await poison_plant(session, world)
    await knowing(session, world.people, FolkDomain.PLANTS, depth=100, accuracy=0)
    tally = FolkTally()
    await keep_folk_knowledge(tuned(ctx, class_span=10, harm_chance_pct=100, harm_hp=10), tally)
    named = await session.scalar(select(FolkClassRow).where(FolkClassRow.grouped_node_id == weed.id))
    assert named is not None and named.taken_as is FolkTaking.FOOD and named.misclassified
    assert tally.learned >= 1 and tally.harmed == 1
    assert stat(victim, "hp") == 50
    assert {"folk.class_learned", "folk.misclassification_harm"} <= set(await kinds_of(session))


async def test_an_illness_taken_for_a_curse_is_blamed_and_stirs_the_town(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town = await home_town(session, world, world.people)
    sickness = await entity(session, "Grey Cough", EntityType.DISEASE, DiseaseStats(), world_id=world.world.id)
    session.add(
        DiseaseProfileRow(
            disease_entity_id=sickness.id,
            primary_route=Transmission.INHALATION,
            affinity_warmth=ClimateWarmth.WARM,
            virulence=30,
            lethality=10,
            chronic_rate=0,
            incubation=1,
            immunity_epochs=5,
            mutation_rate=0,
            stigma=0,
            cure_level=0,
        )
    )
    row = await knowing(session, world.people, FolkDomain.ILLNESS, depth=0, accuracy=0)
    session.add(
        FolkClassRow(
            people_entity_id=world.people.id, domain=FolkDomain.ILLNESS, name="Grey Cough", grouped_node_id=sickness.id, taken_as=FolkTaking.CURSE, locked=[]
        )
    )
    await session.flush()
    await keep_folk_knowledge(tuned(ctx, harm_chance_pct=100, curse_blame_unrest=5), FolkTally())
    profile = await session.get(SettlementProfileRow, town.id)
    assert profile is not None and profile.unrest == 25 and row.accuracy == 0


async def test_neighbours_teach_theories_pull_and_holders_take_knowledge_to_the_grave(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    other = await entity(session, "Ferrow Folk", EntityType.PEOPLE, PeopleStats(), world_id=world.world.id)
    await home_town(session, world, world.people)
    town = await home_town(session, world, other, "Ferrow")
    ours = await knowing(session, world.people, FolkDomain.WEATHER, depth=40, accuracy=30, holders=LoreHolders.EVERYONE)
    await knowing(session, other, FolkDomain.WEATHER, depth=40, accuracy=90, holders=LoreHolders.EVERYONE)
    elders = await knowing(session, other, FolkDomain.TIME, depth=50, accuracy=50, holders=LoreHolders.ELDERS, transmission=LoreTransmission.ORAL)
    dead = await mortal(session, "Old Teller", world, town.id)
    dead.status, dead.end_epoch = EntityStatus.DEAD, ctx.epoch
    await session.flush()
    tally = FolkTally()
    await keep_folk_knowledge(tuned(ctx, contact_gain=5, loss_on_holder_death_pct=100, class_span=10), tally)
    assert ours.accuracy == 35 and tally.exchanged >= 1
    assert elders.depth == 40 and tally.lost == 1
    assert {"folk.lore_exchanged", "folk.lore_lost"} <= set(await kinds_of(session))


async def test_the_number_of_the_epoch_moves_the_towns_of_a_people(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town = await home_town(session, world, world.people)
    number = ctx.epoch % 10
    session.add(NumberSystemRow(people_entity_id=world.people.id, base=10, numerology={str(number): "unlucky"}, locked=[]))
    await session.flush()
    await keep_folk_knowledge(tuned(ctx, numerology_unrest=3), FolkTally())
    profile = await session.get(SettlementProfileRow, town.id)
    assert profile is not None and profile.unrest == 23
    system = await session.get(NumberSystemRow, world.people.id)
    assert system is not None
    system.numerology = {str(number): "sacred"}
    await session.flush()
    await keep_folk_knowledge(tuned(ctx, numerology_piety=3), FolkTally())
    assert stat(town, "piety") == 53
    assert "folk.number_read" in await kinds_of(session)


async def test_accurate_knowledge_lifts_the_work_it_serves(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town = await home_town(session, world, world.people)
    await knowing(session, world.people, FolkDomain.ANIMALS, depth=50, accuracy=100)
    await knowing(session, world.people, FolkDomain.PLANTS, depth=50, accuracy=0)
    rules = tuned_rules(folk_knowledge={"accuracy_success_pct": 50})
    assert await folk_factor(session, rules, town, FolkDomain.ANIMALS) == 1.25
    assert await folk_factor(session, rules, town, FolkDomain.PLANTS) == 0.75
    assert await folk_factor(session, rules, town, FolkDomain.SKY) == 1.0


async def test_a_people_that_watches_the_heavens_keeps_its_sky_lore_right(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    sky = FolkKnowledgeRow(people_entity_id=world.people.id, domain=FolkDomain.SKY, accuracy=0, locked=[])
    session.add(sky)
    bodies = [await entity(session, f"Watched {number}", EntityType.CELESTIAL, CelestialStats(), world_id=world.world.id) for number in range(3)]
    session.add_all(
        CelestialReadingRow(celestial_entity_id=body.id, people_entity_id=world.people.id, reading=OmenReading.NEUTRAL, epoch=1, locked=[]) for body in bodies
    )
    await session.flush()
    await watch_the_heavens(ctx, world.people, sky)
    assert sky.accuracy == min(ctx.rules.forecasting.sky_mark_cap, 3 * ctx.rules.forecasting.sky_mark_accuracy)


async def test_each_people_names_the_land_it_lives_on_and_its_sky_holds_no_own_world(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    far = await entity(session, "Fell Folk", EntityType.PEOPLE, PeopleStats(), world_id=world.world.id, location_id=world.regions[1].id)
    for people in (world.people, far):
        await knowing(session, people, FolkDomain.LAND, depth=100, accuracy=100)
        await knowing(session, people, FolkDomain.SKY, depth=100, accuracy=100)
    await keep_folk_knowledge(tuned(ctx, class_span=100), FolkTally())
    land = {row.people_entity_id: row.grouped_node_id for row in await session.scalars(select(FolkClassRow).where(FolkClassRow.domain == FolkDomain.LAND))}
    assert land == {world.people.id: world.people.location_id, far.id: world.regions[1].id}
    sky = set(await session.scalars(select(FolkClassRow.grouped_node_id).where(FolkClassRow.domain == FolkDomain.SKY)))
    assert world.world.id not in sky
