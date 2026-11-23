from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.renown import DeedRow
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.knowledge import KnowledgeKind
from aerona.domain.enums.renown import ClaimKind, ClaimStatus, LorePrice, ReputationAxis, ServiceTask
from aerona.engine.context import TickContext
from aerona.engine.primitives.manual import manual_context
from aerona.engine.renown.claims import dispute, lay_claim
from aerona.engine.renown.deeds import credit, new_claim
from aerona.engine.renown.lore import perform_services, trade
from tests.engine.core.factories import CoreWorld, mortal, settlement


async def test_an_inflated_claim_is_disputed_and_the_renown_split(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town = await settlement(session, "Hunthold", world, world.regions[0])
    hunter = await mortal(session, "First Hunter", world, town.id)
    boaster = await mortal(session, "Second Hunter", world, town.id)
    deed = DeedRow(doer_node_id=hunter.id, axis=ReputationAxis.HEROISM, magnitude=40, epoch=ctx.epoch, locked=[])
    session.add(deed)
    await session.flush()
    session.add(new_claim(deed.id, hunter.id, ClaimKind.TRUE, ctx.epoch))
    claim = await lay_claim(ctx, deed, boaster.id, ClaimKind.INFLATED)
    assert claim is not None and claim.kind is ClaimKind.INFLATED
    assert await dispute(ctx, claim, hunter.id)
    assert claim.status is ClaimStatus.DISPUTED and claim.contested_by_node_id == hunter.id
    await credit(ctx, deed, town.id, 100, witnessed=True)
    assert claim.credited > 0
    assert not await dispute(ctx, claim, hunter.id)


async def test_knowledge_bought_by_service_passes_only_once_the_deed_is_done(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    seller = await settlement(session, "Lorehold", world, world.regions[0])
    item = (KnowledgeKind.TECHNIQUE, next(iter(Technique)).value, None)
    row = await trade(ctx, seller, world.people, item, value=10, price=LorePrice.SERVICE)
    assert row is not None and not row.passed and isinstance(row.task, ServiceTask)
    cosmos = await session.get(CosmosRow, world.cosmos.id)
    assert cosmos is not None
    cosmos.epoch = ctx.epoch + 1
    await session.flush()
    assert await perform_services(await manual_context(session, "renown")) == 1
    assert row.passed
