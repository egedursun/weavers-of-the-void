from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.concealment import HiddenTruthRow
from aerona.db.tables.disease import DiseaseProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sacred import ForesightRow
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.disease import ClimateWarmth
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import DiseaseStats
from aerona.engine.disease.designed import designed_aim
from aerona.engine.powers.effects import seen_ahead
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement
from tests.engine.core.test_minds_w44 import at


async def test_a_fresh_world_hides_nothing_until_its_seed_history_or_a_god_does(session: AsyncSession, world: CoreWorld) -> None:
    hidden = await session.scalar(select(func.count()).select_from(HiddenTruthRow))
    assert hidden == 0


async def test_a_foresight_is_a_probability_kept_ahead_and_never_rewrites_what_happened(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Farsight", world, world.regions[0])
    seer = await mortal(session, "Ilse", world, town.id)
    before = {row.id: (row.name, row.status) for row in await session.scalars(select(EntityRow))}
    ctx = await at(session, 4)
    row = await seen_ahead(ctx, seer, None, 40, None)
    assert row is not None and isinstance(row, ForesightRow)
    assert 0 <= row.certainty <= 100 and row.due_epoch >= ctx.epoch
    after = {item.id: (item.name, item.status) for item in await session.scalars(select(EntityRow)) if item.id in before}
    assert after == before


async def test_a_disease_made_for_one_people_strikes_them_harder_and_others_less(session: AsyncSession, world: CoreWorld) -> None:
    aimed_at = await settlement(session, "Marked", world, world.regions[0])
    spared = await settlement(session, "Elsewhere", world, world.regions[0])
    plague = await entity(session, "The Made Sickness", EntityType.DISEASE, DiseaseStats(), world_id=world.world.id)
    session.add(
        DiseaseProfileRow(
            disease_entity_id=plague.id,
            primary_route=Transmission.INHALATION,
            affinity_warmth=ClimateWarmth.WARM,
            virulence=50,
            lethality=30,
            chronic_rate=0,
            incubation=1,
            immunity_epochs=5,
            mutation_rate=0,
            stigma=0,
            cure_level=0,
            target_node_id=aimed_at.id,
        )
    )
    await session.flush()
    ctx = await at(session, 2)
    assert await designed_aim(session, ctx.rules, aimed_at, plague.id) > 1.0
    assert await designed_aim(session, ctx.rules, spared, plague.id) < 1.0
