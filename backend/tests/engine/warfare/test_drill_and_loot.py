from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.military import ArmyProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.polity import LawKind
from aerona.engine.military.campaign import bring_home_loot, drill
from aerona.engine.military.units import stacks_of
from aerona.engine.polity.laws import enact
from aerona.engine.primitives.stats import stat
from aerona.engine.primitives.strength import MilitaryStrength
from aerona.engine.services.sides import SideIndex
from aerona.engine.services.war import open_war, raise_army
from aerona.engine.services.war_geography import Neighbourhood
from tests.engine.warfare.factories import make, make_ctx, society


async def test_a_standing_army_drills_and_brings_its_loot_home(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    host = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=20000, wealth=10)
    foe = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=6000)
    await society(session, host.id, warrior=30.0)
    war = await open_war(ctx, host, foe)
    strength = await MilitaryStrength.load(session, ctx.rules)
    army, _ = await raise_army(ctx, strength, await SideIndex.load(session, await Neighbourhood.load(session, ctx.rules)), host, war)
    profile = await session.get(ArmyProfileRow, army.id)
    assert profile is not None
    rows = await stacks_of(session, army.id)
    assert not await drill(ctx, host, profile, rows)
    await enact(ctx, host, LawKind.STANDING_ARMY, {"share": 10})
    drilled, cohesion = profile.drill, profile.cohesion
    assert await drill(ctx, host, profile, rows)
    assert profile.drill > drilled and profile.cohesion >= cohesion
    assert await bring_home_loot(ctx, None, profile) == 0
    profile.loot = 7
    assert await bring_home_loot(ctx, host, profile) == 7
    assert profile.loot == 0 and stat(host, "wealth") == 17
