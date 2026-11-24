from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.disease import ImmunityRow, OutbreakRow
from aerona.domain.enums.demography import AgeBand
from aerona.domain.enums.disease import SpreadPath
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import DiseaseStats, EventStats
from aerona.engine.disease.load import DiseaseLoads
from aerona.engine.happenings.effects import immune_shares
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, entity, settlement


async def test_a_plague_event_is_counted_by_its_peak_and_not_again_as_a_load(session: AsyncSession, world: CoreWorld) -> None:
    region = world.regions[0]
    disease = await entity(session, "The Long Fever", EntityType.DISEASE, DiseaseStats(), world_id=world.world.id)
    event = await entity(session, "The Fever Years", EntityType.EVENT, EventStats(), world_id=world.world.id)
    before = (await DiseaseLoads.load(session, Rules())).of_region(region.id)
    session.add(
        OutbreakRow(
            disease_entity_id=disease.id, region_entity_id=region.id, event_entity_id=event.id, path=next(iter(SpreadPath)), severity=80, started_epoch=1
        )
    )
    await session.flush()
    assert (await DiseaseLoads.load(session, Rules())).of_region(region.id) == before
    session.add(OutbreakRow(disease_entity_id=disease.id, region_entity_id=region.id, path=next(iter(SpreadPath)), severity=80, started_epoch=1))
    await session.flush()
    assert (await DiseaseLoads.load(session, Rules())).of_region(region.id) > before


async def test_folk_immune_to_a_plague_are_spared_at_its_peak(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Reedmouth", world, world.regions[0])
    disease = await entity(session, "The Long Fever", EntityType.DISEASE, DiseaseStats(), world_id=world.world.id)
    event = await entity(session, "The Fever Years", EntityType.EVENT, EventStats(), world_id=world.world.id)
    session.add(
        OutbreakRow(
            disease_entity_id=disease.id,
            region_entity_id=world.regions[0].id,
            event_entity_id=event.id,
            path=next(iter(SpreadPath)),
            severity=80,
            started_epoch=1,
        )
    )
    session.add_all(ImmunityRow(community_entity_id=town.id, disease_entity_id=disease.id, age_band=band, immune_pct=60, since_epoch=1) for band in AgeBand)
    await session.flush()
    spared = await immune_shares(await manual_context(session, "plague_peak"), event)
    assert round(spared[town.id], 2) == 0.6
