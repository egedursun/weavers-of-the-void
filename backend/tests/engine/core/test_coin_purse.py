from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.polity import DecisionRule, GovernmentKind
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.economy.purse import coin_of, give_coin, take_coin, wealth_points
from aerona.engine.lore.great_people import monopoly
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import set_stats, stat
from tests.engine.core.factories import CoreWorld, entity, settlement


async def test_treasury_is_spent_from_the_realm_then_from_wealth_at_its_rate(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test")
    rate = ctx.rules.taxation.wealth_per_treasury
    town = await settlement(session, "Brookhold", world, world.regions[0])
    set_stats(town, wealth=10)
    assert wealth_points(ctx.rules, 0) == 0 and wealth_points(ctx.rules, 1) == 1 and wealth_points(ctx.rules, 3 * rate) == 3
    assert await coin_of(session, ctx.rules, town) == 10 * rate
    assert await take_coin(session, ctx.rules, town, 4 * rate) and stat(town, "wealth") == 6
    assert not await take_coin(session, ctx.rules, town, 100 * rate)
    polity = await entity(session, "Kingdom of Vale", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    realm = PolityProfileRow(
        polity_entity_id=polity.id,
        government=next(iter(GovernmentKind)),
        decision_rule=next(iter(DecisionRule)),
        treasury=500,
        emblem={},
        legitimacy_parts={},
        locked=[],
    )
    session.add_all([realm, PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id)])
    await session.flush()
    assert await take_coin(session, ctx.rules, town, 300) and realm.treasury == 200 and stat(town, "wealth") == 6
    realm.locked = ["treasury"]
    assert await coin_of(session, ctx.rules, town) == 6 * rate
    give_coin(ctx.rules, town, 2 * rate)
    assert stat(town, "wealth") == 8


async def test_a_monopoly_without_a_realm_pays_wealth_at_the_treasury_rate(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test")
    town = await settlement(session, "Brookhold", world, world.regions[0])
    set_stats(town, wealth=10)
    assert await monopoly(ctx, town)
    assert stat(town, "wealth") == 10 + wealth_points(ctx.rules, ctx.rules.discovery.great_wealth)
