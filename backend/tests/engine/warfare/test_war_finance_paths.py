from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.military import ArmyProfileRow, MercenaryContractRow
from aerona.db.tables.mind import CultureValueRow
from aerona.db.tables.warfare import WarSideRow
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.military import ContractStatus
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.war import WarStatus
from aerona.engine.military.finance import pay_contracts
from aerona.engine.military.occupation import pay_occupier, seeks_peace
from aerona.engine.military.upkeep import hire_mercenaries, open_wars
from aerona.engine.primitives.stats import stat
from aerona.engine.primitives.strength import MilitaryStrength
from aerona.engine.services.sides import SideIndex
from aerona.engine.services.war import open_war, raise_army
from aerona.engine.services.war_geography import Neighbourhood
from tests.engine.warfare.factories import make, make_ctx, society


async def test_a_weary_side_seeks_peace_unless_honour_holds_it(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    first = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000)
    second = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=6000)
    war = await open_war(ctx, first, second)
    side = await session.get(WarSideRow, (war.id, first.id))
    assert side is not None
    side.weariness, side.support = 0, 100
    assert not await seeks_peace(ctx, war, side, humiliated=False)
    side.weariness = ctx.rules.war_weariness.peace_threshold
    assert await seeks_peace(ctx, war, side, humiliated=False)
    session.add(CultureValueRow(entity_id=first.id, axis=ValueAxis.HONOUR, value=80))
    await session.flush()
    assert not await seeks_peace(ctx, war, side, humiliated=True)


async def test_occupation_tax_fills_the_occupiers_war_chest_or_purse(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    occupier = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000, wealth=10)
    other = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=6000)
    await pay_occupier(ctx, occupier.id, 1000 * ctx.rules.taxation.wealth_per_treasury)
    assert (stat(occupier, "wealth") or 0) > 10
    await society(session, occupier.id)
    war = await open_war(ctx, occupier, other)
    strength = await MilitaryStrength.load(session, ctx.rules)
    army, _ = await raise_army(ctx, strength, await SideIndex.load(session, await Neighbourhood.load(session, ctx.rules)), occupier, war)
    profile = await session.get(ArmyProfileRow, army.id)
    assert profile is not None
    chest = profile.war_chest
    await pay_occupier(ctx, occupier.id, 50)
    assert profile.war_chest == chest + 50


async def test_an_outnumbered_side_with_coin_hires_a_free_company(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    small = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=600, wealth=100)
    great = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=20000)
    await make(session, "The Grey Company", EntityType.FACTION, world_id, engine_kind=EngineKind.WARRIOR_BAND, sway=50)
    await society(session, great.id, warrior=30.0)
    war = await open_war(ctx, great, small)
    war.status = WarStatus.ONGOING
    strength = await MilitaryStrength.load(session, ctx.rules)
    await raise_army(ctx, strength, await SideIndex.load(session, await Neighbourhood.load(session, ctx.rules)), great, war)
    assert war in await open_wars(ctx)
    assert await hire_mercenaries(ctx) == 1
    contract = await session.scalar(select(MercenaryContractRow).where(MercenaryContractRow.employer_entity_id == small.id))
    assert contract is not None and contract.war_id == war.id and contract.soldiers > 100 * PERCENT // 6
    assert await hire_mercenaries(ctx) == 0
    found = await pay_contracts(ctx)
    assert found["paid"] == 1 and (stat(small, "wealth") or 0) < 100
    assert contract.unpaid_seasons == 0 and contract.status is not ContractStatus.TURNED
