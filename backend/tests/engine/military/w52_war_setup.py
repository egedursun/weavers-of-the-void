from aerona.db.tables.military import ArmyProfileRow, ArmyUnitRow
from aerona.db.tables.warfare import ArmyRow, SiegeRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.military import Stance, UnitKind
from aerona.domain.models.entity_stats import ArmyStats
from aerona.engine.context import TickContext
from aerona.engine.services.war import open_war
from tests.engine.warfare.factories import make
from tests.tools.factories import make_entity


async def army_of(ctx: TickContext, owner_id: int, world_id: int, *, kind: UnitKind = UnitKind.LEVY, count: int = 200) -> tuple[int, ArmyProfileRow]:
    army = await make_entity(
        ctx.session, f"Host of the {kind.value.replace('_', ' ')}", EntityType.ARMY, world_id=world_id, stats=ArmyStats(size=count, morale=60)
    )
    ctx.session.add(ArmyRow(entity_id=army.id, owner_entity_id=owner_id, raised_epoch=1))
    profile = ArmyProfileRow(army_entity_id=army.id, stance=Stance.MARCH, doctrine="shieldwall", supply_line=[], locked=[])
    ctx.session.add(profile)
    ctx.session.add(ArmyUnitRow(army_entity_id=army.id, kind=kind, count=count, origin_entity_id=owner_id, locked=[]))
    await ctx.session.flush()
    return army.id, profile


async def siege_of(ctx: TickContext, world_id: int) -> tuple[int, int, SiegeRow]:
    attacker = await make(ctx.session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000)
    city = await make(ctx.session, "Highwall", EntityType.SETTLEMENT, world_id, population=2000, prosperity=50, defense=40)
    war = await open_war(ctx, attacker, city)
    siege = SiegeRow(war_id=war.id, besieged_entity_id=city.id, besieger_entity_id=attacker.id, started_epoch=ctx.epoch, works={}, locked=[])
    ctx.session.add(siege)
    await ctx.session.flush()
    return attacker.id, city.id, siege
