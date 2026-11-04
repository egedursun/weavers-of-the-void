from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyProfileRow
from aerona.db.tables.settlement import SettlementInfrastructureRow, SettlementProfileRow
from aerona.db.tables.warfare import SiegeRow, WarRow
from aerona.domain.enums.military import DefenderAction, SiegeAction, StarvationStage, UnitKind
from aerona.domain.enums.war import SiegeStatus
from aerona.engine.context import TickContext
from aerona.engine.economy.equipment import siege_engines
from aerona.engine.lore.art import smash
from aerona.engine.military.logistics import March, desert, dishearten
from aerona.engine.military.units import stacks_of, sync, take
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat, stat

DEFAULT_SUPPLIES = 180
DEFAULT_WATER = 120
HALF = 2


@dataclass
class SiegeSeason:
    siege: SiegeRow
    action: SiegeAction
    defence: DefenderAction
    assault: bool = False
    surrendered: bool = False
    sally_dead: int = 0


async def open_siege(ctx: TickContext, war: WarRow, besieged: EntityRow, besieger: EntityRow) -> SiegeRow:
    statement = select(SiegeRow).where(SiegeRow.war_id == war.id, SiegeRow.besieged_entity_id == besieged.id, SiegeRow.status == SiegeStatus.ONGOING)
    row = await ctx.session.scalar(statement.limit(1))
    if row is not None:
        return row
    town = await ctx.session.get(SettlementProfileRow, besieged.id)
    walls = await ctx.session.get(SettlementInfrastructureRow, besieged.id)
    row = SiegeRow(
        war_id=war.id,
        besieged_entity_id=besieged.id,
        besieger_entity_id=besieger.id,
        status=SiegeStatus.ONGOING,
        started_epoch=ctx.epoch,
        rounds=0,
        walls_level=walls.walls_level if walls is not None else 0,
        breaches=0,
        supplies=town.siege_supplies if town is not None and town.siege_supplies > 0 else DEFAULT_SUPPLIES,
        water=town.siege_water if town is not None and town.siege_water > 0 else DEFAULT_WATER,
        disease_inside=town.siege_disease if town is not None else 0,
        disease_outside=0,
        works={},
        sallies=0,
        starvation=StarvationStage.NONE,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


def starve(ctx: TickContext, siege: SiegeRow, rationing: bool) -> None:
    table = ctx.rules.siegecraft
    days = ctx.rules.logistics.season_days
    eaten = round_half_up(days * table.ration_use_pct / PERCENT) if rationing else days
    siege.supplies = max(0, siege.supplies - eaten)
    siege.water = max(0, siege.water - days)
    hungry = siege.supplies <= table.famine_days or siege.water <= table.famine_days
    if not hungry:
        siege.starvation = StarvationStage.RATIONING if rationing else StarvationStage.NONE
        return
    famine = int(siege.works.get("famine", 0)) + 1
    siege.works = {**siege.works, "famine": famine}
    siege.starvation = StarvationStage.TABOO_BROKEN if famine > table.taboo_seasons else StarvationStage.FAMINE


def defence_for(ctx: TickContext, siege: SiegeRow, garrison: int, besiegers: int, walls: SettlementInfrastructureRow | None) -> DefenderAction:
    table = ctx.rules.siegecraft
    condition = walls.walls_condition if walls is not None else PERCENT
    if besiegers and garrison * PERCENT >= besiegers * table.sally_ratio_pct:
        return DefenderAction.SALLY
    if siege.breaches > 0 or condition < table.breach_condition:
        return DefenderAction.REPAIR
    if siege.supplies < ctx.rules.urban.ration_supplies_days:
        return DefenderAction.RATION
    return DefenderAction.SEEK_RELIEF


async def action_for(ctx: TickContext, siege: SiegeRow, march: March, engines: float) -> SiegeAction:
    table = ctx.rules.siegecraft
    if siege.breaches >= table.assault_breaches and table.assault_breaches > 0:
        return SiegeAction.ASSAULT
    if siege.starvation in {StarvationStage.FAMINE, StarvationStage.TABOO_BROKEN}:
        return SiegeAction.NEGOTIATE
    rows = await stacks_of(ctx.session, march.army.id)
    if any(row.kind is UnitKind.SAPPERS and row.count > 0 for row in rows):
        return SiegeAction.MINE
    if engines > 0:
        return SiegeAction.BOMBARD
    if siege.starvation is StarvationStage.RATIONING:
        return SiegeAction.NEGOTIATE
    return SiegeAction.BLOCKADE


def batter(ctx: TickContext, siege: SiegeRow, walls: SettlementInfrastructureRow | None, action: SiegeAction, engines: float) -> None:
    table = ctx.rules.siegecraft
    if walls is None:
        siege.breaches += 1 if action in {SiegeAction.BOMBARD, SiegeAction.MINE} else 0
        return
    if action is SiegeAction.BOMBARD:
        walls.walls_condition = clamp_int(walls.walls_condition - round_half_up(table.bombard_breach * engines), 0, PERCENT)
    if action is SiegeAction.MINE and ctx.rng(f"mine.{siege.id}.{siege.rounds}").chance(table.mine_chance):
        walls.walls_condition = clamp_int(walls.walls_condition - table.bombard_breach, 0, PERCENT)
        siege.works = {**siege.works, "mines": int(siege.works.get("mines", 0)) + 1}
    if walls.walls_condition < table.breach_condition:
        siege.breaches = max(siege.breaches, 1)


def mend(ctx: TickContext, siege: SiegeRow, walls: SettlementInfrastructureRow | None) -> None:
    if walls is None:
        return
    walls.walls_condition = clamp_int(walls.walls_condition + ctx.rules.siegecraft.repair_pct, 0, PERCENT)
    if walls.walls_condition >= ctx.rules.siegecraft.breach_condition:
        siege.breaches = max(0, siege.breaches - 1)


async def sally(ctx: TickContext, siege: SiegeRow, march: March) -> int:
    rows = await stacks_of(ctx.session, march.army.id)
    lost = take(rows, round_half_up((stat(march.army, "size") or 0) * ctx.rules.siegecraft.sally_losses_pct / PERCENT))
    sync(march.army, rows, ctx.rules)
    siege.sallies += 1
    return lost


def surrenders(ctx: TickContext, siege: SiegeRow, action: SiegeAction) -> bool:
    table = ctx.rules.siegecraft
    rng = ctx.rng(f"surrender.{siege.id}.{siege.rounds}")
    if siege.starvation is StarvationStage.TABOO_BROKEN:
        return rng.chance(table.surrender_chance * HALF)
    if siege.starvation is StarvationStage.FAMINE:
        return rng.chance(table.surrender_chance)
    return action is SiegeAction.NEGOTIATE and rng.chance(table.negotiate_chance)


async def siege_season(ctx: TickContext, war: WarRow, besieged: EntityRow, march: March, garrison: int) -> SiegeSeason:
    siege = await open_siege(ctx, war, besieged, march.owner)
    siege.rounds += 1
    walls = await ctx.session.get(SettlementInfrastructureRow, besieged.id)
    engines = await siege_engines(ctx, march.owner, march.army)
    defence = defence_for(ctx, siege, garrison, stat(march.army, "size") or 0, walls)
    starve(ctx, siege, defence is DefenderAction.RATION or siege.starvation is not StarvationStage.NONE)
    action = await action_for(ctx, siege, march, engines)
    batter(ctx, siege, walls, action, engines)
    found = SiegeSeason(siege, action, defence)
    if defence is DefenderAction.SALLY:
        found.sally_dead = await sally(ctx, siege, march)
    elif defence is DefenderAction.REPAIR:
        mend(ctx, siege, walls)
    siege.disease_outside = clamp_int(siege.disease_outside + ctx.rules.siegecraft.camp_disease_gain, 0, PERCENT)
    march.profile.disease = max(march.profile.disease, siege.disease_outside)
    town = await ctx.session.get(SettlementProfileRow, besieged.id)
    if town is not None:
        siege.disease_inside = town.siege_disease
        town.siege_supplies, town.siege_water = siege.supplies, siege.water
    siege.last_action, siege.last_defence = action, defence
    found.surrendered = surrenders(ctx, siege, action)
    found.assault = not found.surrendered and action is SiegeAction.ASSAULT
    return found


def wall_defence(ctx: TickContext, siege: SiegeRow) -> float:
    return 1 + siege.walls_level * ctx.rules.siegecraft.wall_defence_pct / PERCENT / max(1, siege.breaches + 1)


async def sack(ctx: TickContext, besieged: EntityRow, profile: ArmyProfileRow | None, *, homeward: list[March]) -> int:
    table = ctx.rules.siegecraft
    wealth = stat(besieged, "wealth") or stat(besieged, "prosperity") or 0
    taken = min(wealth, table.sack_loot)
    for key in ("wealth", "prosperity"):
        if stat(besieged, key) is not None:
            shift_stat(besieged, key, -(taken if key == "wealth" else table.sack_prosperity))
    if profile is not None:
        profile.loot += taken
    population = stat(besieged, "population")
    dead = round_half_up((population or 0) * ctx.rules.terrain_effects.urban_civilian_pct / PERCENT)
    if population is not None and dead:
        shift_stat(besieged, "population", -dead)
    morale = ctx.rules.morale
    for march in homeward:
        rows = await stacks_of(ctx.session, march.army.id)
        dishearten(rows, -morale.home_sacked_rage)
        desert(ctx.rules, march, rows, round_half_up((stat(march.army, "size") or 0) * morale.home_sacked_desertion_pct / PERCENT))
        sync(march.army, rows, ctx.rules)
    ctx.count("sacks")
    ctx.count("sacked_images", len(await smash(ctx, besieged.id, ctx.rules.art.sack_chance, "broken by the army that sacked the city")))
    return dead
