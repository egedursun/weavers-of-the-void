from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.military import army_sheet, order_line, war_sheet
from aerona.domain.enums.entity import EntityType
from aerona.engine.primitives.strength import MilitaryStrength
from aerona.engine.services.sides import SideIndex
from aerona.engine.services.war import open_war, raise_army
from aerona.engine.services.war_geography import Neighbourhood
from tests.engine.warfare.factories import make, make_ctx, society


async def test_a_side_at_war_reads_the_sheets_of_its_armies(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    first = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000, wealth=40)
    second = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=6000, wealth=40)
    await society(session, first.id)
    war = await open_war(ctx, first, second)
    strength = await MilitaryStrength.load(session, ctx.rules)
    army, _ = await raise_army(ctx, strength, await SideIndex.load(session, await Neighbourhood.load(session, ctx.rules)), first, war)
    sheet = await army_sheet(session, ctx.rules, army.id)
    assert sheet.startswith(f"{army.name}: ") and "soldiers" in sheet and "the land feeds about" in sheet
    lines = await war_sheet(session, ctx.rules, war, first.id)
    assert sheet in lines
    assert await war_sheet(session, ctx.rules, war, second.id) == [] or all(
        not line.startswith(army.name) for line in await war_sheet(session, ctx.rules, war, second.id)
    )
    assert await army_sheet(session, ctx.rules, 999999) == ""
    assert order_line([]) == ""
