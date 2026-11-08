from sqlalchemy.ext.asyncio import AsyncSession

from aerona.domain.enums.settlement import BuildMaterial
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.manual import manual_context
from aerona.engine.settlement.book import town_of
from aerona.engine.settlement.readout import defences_of, plan_readout
from tests.engine.core.factories import CoreWorld, settlement


async def test_a_towns_plan_reads_its_walls_stores_and_prestige(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "plan")
    place = await settlement(session, "Brookhold", world, world.regions[0], population=6000)
    town = await town_of(ctx, place, await KnowledgeMap.load(session))
    walls = town.infrastructure
    walls.walls_level, walls.walls_material, walls.towers, walls.gates = 2, BuildMaterial.STONE, 3, 3
    town.profile.prestige = 50
    rules = ctx.rules
    stone = defences_of(rules, town)
    assert stone.wall_pct == round(2 * rules.siegecraft.wall_defence_pct * rules.districts.stone_wall_pct / 100)
    assert stone.tower_pct == 3 * rules.districts.tower_defence_pct and stone.gate_weakness_pct == 2 * rules.districts.gate_breach_pct
    assert stone.batter_pct == rules.siege_depth.stone_bombard_pct
    walls.walls_material, walls.gates = BuildMaterial.TIMBER, 1
    timber = defences_of(rules, town)
    assert timber.batter_pct == rules.siege_depth.timber_bombard_pct and timber.gate_weakness_pct == 0
    readout = await plan_readout(session, rules, town)
    assert readout.defences == timber
    assert readout.prestige_pull_pct == round(50 * rules.districts.prestige_pull_pct / 100)
    assert readout.food.other >= 0 and readout.goods.other >= 0
    assert readout.admin is not None and readout.designs == []
