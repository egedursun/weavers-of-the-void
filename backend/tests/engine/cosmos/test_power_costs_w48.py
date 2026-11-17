from sqlalchemy import select

from aerona.catalog.kinds.power_costs import POWER_COSTS
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.powers import PowerCost
from aerona.domain.models.entity_stats import MortalStats, SettlementStats
from aerona.engine.context import TickContext
from aerona.engine.powers.sources import draw_souls, patron_can_pay, take_cost
from tests.engine.cosmos.factories import Cosmos, make_entity, make_son


async def town_with(ctx: TickContext, cosmos: Cosmos, *names: str) -> list[EntityRow]:
    town = await make_entity(ctx.session, "Harl", EntityType.SETTLEMENT, SettlementStats(population=500), world_id=cosmos.home.id)
    folk = [await make_entity(ctx.session, name, EntityType.MORTAL, MortalStats(hp=50), world_id=cosmos.home.id, location_id=town.id) for name in names]
    return [town, *folk]


def test_essence_and_soul_costs_draw_on_the_patron_and_on_others() -> None:
    assert POWER_COSTS[PowerCost.ESSENCE].draws == "patron"
    assert POWER_COSTS[PowerCost.SOUL].draws == "souls"


async def test_an_essence_cost_is_paid_by_the_user_s_patron_god(ctx: TickContext, cosmos: Cosmos) -> None:
    _, user = await town_with(ctx, cosmos, "Ira")
    son = await make_son(ctx.session, "Velo", cosmos.home.id)
    await BondRepository(ctx.session).connect(BondDraft(user.id, son.id, BondKind.WORSHIPS, 1))
    before = son.essence
    await take_cost(ctx, user, "patron", 10)
    assert son.essence == before - 10


async def test_without_a_patron_able_to_pay_the_essence_cost_cannot_be_met(ctx: TickContext, cosmos: Cosmos) -> None:
    _, user = await town_with(ctx, cosmos, "Ira")
    assert await patron_can_pay(ctx, user, 10) is False
    son = await make_son(ctx.session, "Velo", cosmos.home.id)
    son.essence = 3
    await BondRepository(ctx.session).connect(BondDraft(user.id, son.id, BondKind.WORSHIPS, 1))
    assert await patron_can_pay(ctx, user, 10) is False
    assert await patron_can_pay(ctx, user, 3) is True


async def test_a_soul_cost_takes_life_from_the_beings_around_the_user(ctx: TickContext, cosmos: Cosmos) -> None:
    _, user, first, second = await town_with(ctx, cosmos, "Ira", "Bel", "Cas")
    assert await draw_souls(ctx, user, 20) == 2
    await ctx.session.flush()
    harmed = set(await ctx.session.scalars(select(InjuryRow.bearer_node_id).where(InjuryRow.bearer_node_id.in_([user.id, first.id, second.id]))))
    assert harmed == {first.id, second.id}
