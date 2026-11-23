import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.outer_bargains import BARGAIN_PRICES
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.culture import HolderLevelRow
from aerona.db.tables.foreign_gods import OuterBargainRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.divine import BargainGain, BargainPrice, LawException
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.society import NaturalLaw
from aerona.domain.models.entity_stats import CultStats, OuterBeingStats, PeopleStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.actions import BargainTerms, bargain_with_outer
from aerona.engine.divine.control import edit_law
from aerona.engine.divine.laws import exempt
from aerona.engine.divine.outer import due_lines
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import stat
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, natural_law

LAW = next(law for law in NaturalLaw if law is not NaturalLaw.NONE)


async def at(session: AsyncSession, epoch: int) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "w52_laws")


async def test_a_law_spares_the_kind_it_names_and_only_that_kind(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 4)
    law = await natural_law(session, world, "The Even Fall", LAW)
    other = await entity(session, "The Far Folk", EntityType.PEOPLE, PeopleStats(), world_id=world.world.id)
    with pytest.raises(ValidationFailedError):
        await edit_law(ctx, law.id, {"exception": LawException.NAMED_KIND.value}, [])
    with pytest.raises(ValidationFailedError):
        await edit_law(ctx, law.id, {"exception": LawException.NAMED_KIND.value, "exempt_kind_entity_id": world.regions[0].id}, [])
    row = await edit_law(ctx, law.id, {"exception": LawException.NAMED_KIND.value, "exempt_kind_entity_id": world.people.id}, [])
    assert row.exempt_kind_entity_id == world.people.id
    assert await exempt(ctx, world.people, LAW)
    assert not await exempt(ctx, other, LAW)
    row = await edit_law(ctx, law.id, {"exception": LawException.HEROES.value}, [])
    assert row.exempt_kind_entity_id is None


async def test_a_bargain_for_longer_life_takes_worshippers_from_the_faithful(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 4)
    being = await entity(session, "The Patient Mouth", EntityType.OUTER_BEING, OuterBeingStats(size=40, interest=50, influence=30), world_id=world.world.id)
    cult = await entity(session, "The Kneeling", EntityType.CULT, CultStats(followers=400), world_id=world.world.id)
    await bond(session, cult.id, world.son.id, BondKind.WORSHIPS)
    world.son.existence, world.son.fading_epochs = 40, 3
    await bargain_with_outer(ctx, world.son.id, being.id, "more years", BargainTerms(gain=BargainGain.LONGEVITY, price=BargainPrice.WORSHIPPERS))
    assert world.son.existence == 40 + ctx.rules.outer_bargains.longevity_size and world.son.fading_epochs == 0
    assert stat(cult, "followers") == 400 - 400 * ctx.rules.outer_bargains.worshippers_taken_pct // 100
    row = await session.get(OuterBargainRow, (being.id, world.son.id))
    assert row is not None and row.paid is not BARGAIN_PRICES[BargainPrice.WORSHIPPERS].lasting


async def test_a_line_given_for_knowledge_stays_bound_until_its_span_ends(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 4)
    being = await entity(session, "The Listening Deep", EntityType.OUTER_BEING, OuterBeingStats(size=40, interest=50, influence=30), world_id=world.world.id)
    child = await mortal(session, "Ive", world, world.regions[0].id)
    await bond(session, world.son.id, child.id, BondKind.PARENT_OF)
    await bond(session, world.people.id, world.son.id, BondKind.WORSHIPS)
    await bargain_with_outer(ctx, world.son.id, being.id, "what they know", BargainTerms(gain=BargainGain.KNOWLEDGE, price=BargainPrice.DESCENDANTS))
    row = await session.get(OuterBargainRow, (being.id, world.son.id))
    assert row is not None and not row.paid
    assert await session.scalar(select(AfflictionRow.id).where(AfflictionRow.bearer_node_id == child.id)) is not None
    learned = await session.scalars(select(HolderLevelRow).where(HolderLevelRow.holder_entity_id == world.people.id, HolderLevelRow.progress > 0))
    assert list(learned)
    span = ctx.rules.outer_bargains.epochs(ctx.rules.outer_bargains.descendants_years)
    assert await due_lines(await at(session, 4 + span - 1)) == 0 and not row.paid
    assert await due_lines(await at(session, 4 + span)) == 1 and row.paid
