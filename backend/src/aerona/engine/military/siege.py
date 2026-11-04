from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyProfileRow
from aerona.db.tables.settlement import SettlementInfrastructureRow, SettlementProfileRow
from aerona.db.tables.warfare import SiegeRow, WarRow
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.environment import ScarKind
from aerona.domain.enums.military import DefenderAction, SackChoice, SiegeAction, StarvationStage, UnitKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.settlement import BuildMaterial, DistrictHarm
from aerona.domain.enums.war import SiegeStatus
from aerona.engine.context import TickContext
from aerona.engine.economy.equipment import siege_engines
from aerona.engine.environment.book import region_environment, scar_region
from aerona.engine.happenings.emergence import record_sack
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.lore.art import smash
from aerona.engine.military.logistics import March, desert, dishearten
from aerona.engine.military.siege_depth import (
    bombard_factor,
    build_works,
    burn_districts,
    countermine,
    defender_choice,
    hunger_betrayal,
    infamy,
    maim,
    mason_repair,
    mass_captives,
    mining_factor,
    plunder_relics,
    relief_arrived,
    repair_factor,
    seek_relief,
    siege_sickness,
    taboo_holds,
    wall_material,
    water_days,
    works_breach,
)
from aerona.engine.military.units import stacks_of, sync, take
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.services.community_relations import change_relation
from aerona.engine.settlement.districts import damage_districts

DEFAULT_SUPPLIES = 180
HALF = 2


@dataclass
class SiegeSeason:
    siege: SiegeRow
    action: SiegeAction
    defence: DefenderAction
    assault: bool = False
    surrendered: bool = False
    sally_dead: int = 0
    betrayed: bool = False
    relieved: bool = False


@dataclass
class SackReport:
    choice: SackChoice
    dead: int = 0
    captives: int = 0
    relics: int = 0
    maimed: int = 0
    districts: int = 0
    witnesses: int = 0


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
        water=town.siege_water if town is not None and town.siege_water > 0 else water_days(walls),
        disease_inside=town.siege_disease if town is not None else 0,
        disease_outside=0,
        works={},
        sallies=0,
        starvation=StarvationStage.NONE,
        wall_material=walls.walls_material.value if walls is not None else None,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def starve(ctx: TickContext, siege: SiegeRow, besieged: EntityRow, rationing: bool) -> None:
    table = ctx.rules.siegecraft
    if "starvation" in siege.locked:
        return
    days = ctx.rules.logistics.season_days
    eaten = round_half_up(days * table.ration_use_pct / PERCENT) if rationing else days
    if "supplies" not in siege.locked:
        siege.supplies = max(0, siege.supplies - eaten)
    if "water" not in siege.locked:
        siege.water = max(0, siege.water - days)
    hungry = siege.supplies <= table.famine_days or siege.water <= table.famine_days
    if not hungry:
        siege.starvation = StarvationStage.RATIONING if rationing else StarvationStage.NONE
        return
    famine = int(siege.works.get("famine", 0)) + 1
    siege.works = {**siege.works, "famine": famine}
    broke = famine > table.taboo_seasons and not await taboo_holds(ctx, besieged)
    siege.starvation = StarvationStage.TABOO_BROKEN if broke else StarvationStage.FAMINE


async def action_for(ctx: TickContext, siege: SiegeRow, march: March, engines: float) -> SiegeAction:
    table = ctx.rules.siegecraft
    if siege.last_action is not None and "last_action" in siege.locked:
        return siege.last_action
    rows = await stacks_of(ctx.session, march.army.id)
    sappers = any(row.kind is UnitKind.SAPPERS and row.count > 0 for row in rows)
    choices = (
        (siege.breaches >= table.assault_breaches > 0, SiegeAction.ASSAULT),
        (siege.starvation in {StarvationStage.FAMINE, StarvationStage.TABOO_BROKEN}, SiegeAction.NEGOTIATE),
        (sappers, SiegeAction.MINE),
        (engines > 0, SiegeAction.BOMBARD),
        (siege.starvation is StarvationStage.RATIONING, SiegeAction.NEGOTIATE),
    )
    return next((action for hit, action in choices if hit), SiegeAction.BLOCKADE)


def gate_factor(ctx: TickContext, walls: SettlementInfrastructureRow) -> float:
    return 1 + max(0, walls.gates - 1) * ctx.rules.districts.gate_breach_pct / PERCENT


async def batter(ctx: TickContext, siege: SiegeRow, walls: SettlementInfrastructureRow | None, action: SiegeAction, engines: float) -> None:
    table = ctx.rules.siegecraft
    if walls is None:
        siege.breaches += 1 if action in {SiegeAction.BOMBARD, SiegeAction.MINE} else 0
        return
    material = wall_material(walls, siege)
    gates = gate_factor(ctx, walls)
    if action is SiegeAction.BOMBARD and "walls_condition" not in (walls.locked or []):
        damage = round_half_up(table.bombard_breach * engines * bombard_factor(ctx, material) * gates)
        walls.walls_condition = clamp_int(walls.walls_condition - damage, 0, PERCENT)
    if action is SiegeAction.MINE:
        ground = await region_environment(ctx.session, siege.besieged_entity_id)
        if ctx.rng(f"mine.{siege.id}.{siege.rounds}").chance(table.mine_chance * mining_factor(ctx, ground)) and "walls_condition" not in (walls.locked or []):
            walls.walls_condition = clamp_int(walls.walls_condition - round_half_up(table.bombard_breach * gates), 0, PERCENT)
    if walls.walls_condition < table.breach_condition and "breaches" not in siege.locked:
        siege.breaches = max(siege.breaches, 1)


def mend(ctx: TickContext, siege: SiegeRow, walls: SettlementInfrastructureRow | None) -> None:
    if walls is None or "walls_condition" in (walls.locked or []):
        return
    gain = round_half_up(ctx.rules.siegecraft.repair_pct * repair_factor(ctx, wall_material(walls, siege)))
    walls.walls_condition = clamp_int(walls.walls_condition + gain, 0, PERCENT)
    if walls.walls_condition >= ctx.rules.siegecraft.breach_condition and "breaches" not in siege.locked:
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
    atlas = await RegionAtlas.load(ctx.session)
    walls = await ctx.session.get(SettlementInfrastructureRow, besieged.id)
    engines = await siege_engines(ctx, march.owner, march.army)
    defence = defender_choice(ctx, siege, garrison, stat(march.army, "size") or 0, walls)
    await starve(ctx, siege, besieged, defence is DefenderAction.RATION or siege.starvation is not StarvationStage.NONE)
    action = await action_for(ctx, siege, march, engines)
    build_works(ctx, siege, action)
    await batter(ctx, siege, walls, action, engines)
    found = SiegeSeason(siege, action, defence)
    if defence is DefenderAction.SALLY:
        found.sally_dead = await sally(ctx, siege, march)
    elif defence is DefenderAction.REPAIR:
        mend(ctx, siege, walls)
        await mason_repair(ctx, siege, besieged, walls)
        countermine(ctx, siege)
    elif defence is DefenderAction.SEEK_RELIEF:
        relief = await seek_relief(ctx, siege, besieged, atlas)
        if relief is not None:
            ctx.count("siege_relief_called")
    siege.disease_outside = clamp_int(siege.disease_outside + ctx.rules.siegecraft.camp_disease_gain, 0, PERCENT)
    march.profile.disease = max(march.profile.disease, siege.disease_outside)
    await siege_sickness(ctx, siege, besieged)
    town = await ctx.session.get(SettlementProfileRow, besieged.id)
    if town is not None:
        siege.disease_inside = town.siege_disease
        if "siege_supplies" not in town.locked:
            town.siege_supplies = siege.supplies
        if "siege_water" not in town.locked:
            town.siege_water = siege.water
    siege.last_action, siege.last_defence = action, defence
    if await relief_arrived(ctx, siege, besieged, march.army, atlas):
        found.relieved = True
        return found
    found.betrayed = await hunger_betrayal(ctx, siege, besieged)
    found.surrendered = found.betrayed or surrenders(ctx, siege, action)
    found.assault = not found.surrendered and action is SiegeAction.ASSAULT
    return found


def wall_defence(ctx: TickContext, siege: SiegeRow, walls: SettlementInfrastructureRow | None = None) -> float:
    table = ctx.rules.districts
    material = (table.stone_wall_pct if walls.walls_material is BuildMaterial.STONE else table.timber_wall_pct) / PERCENT if walls is not None else 1.0
    towers = walls.towers * table.tower_defence_pct / PERCENT if walls is not None else 0.0
    return 1 + (siege.walls_level * ctx.rules.siegecraft.wall_defence_pct / PERCENT * material + towers) / max(1, siege.breaches + 1)


def breach_bonus(ctx: TickContext, siege: SiegeRow) -> float:
    return works_breach(ctx, siege)


async def sack(
    ctx: TickContext,
    besieged: EntityRow,
    profile: ArmyProfileRow | None,
    *,
    homeward: list[March],
    victor: EntityRow | None = None,
    siege: SiegeRow | None = None,
    choice: SackChoice = SackChoice.SACK,
) -> int:
    report = await sack_city(ctx, besieged, profile, homeward=homeward, victor=victor, siege=siege, choice=choice)
    return report.dead


async def sack_city(
    ctx: TickContext,
    besieged: EntityRow,
    profile: ArmyProfileRow | None,
    *,
    homeward: list[March],
    victor: EntityRow | None,
    siege: SiegeRow | None,
    choice: SackChoice,
) -> SackReport:
    table = ctx.rules.siegecraft
    depth = ctx.rules.siege_depth
    report = SackReport(choice)
    if choice is SackChoice.MERCY:
        if victor is not None:
            await change_relation(ctx, besieged.id, victor.id, depth.infamy, MemoryKind.GOODWILL, note="spared the city")
        ctx.count("cities_spared")
        return report
    wealth = stat(besieged, "wealth") or stat(besieged, "prosperity") or 0
    taken = min(wealth, table.sack_loot)
    for key in ("wealth", "prosperity"):
        if stat(besieged, key) is not None:
            shift_stat(besieged, key, -(taken if key == "wealth" else table.sack_prosperity))
    if profile is not None:
        profile.loot += taken
    population = stat(besieged, "population")
    share = depth.raze_population_pct if choice is SackChoice.RAZE else ctx.rules.terrain_effects.urban_civilian_pct
    report.dead = round_half_up((population or 0) * share / PERCENT)
    if population is not None and report.dead:
        with flowing(FlowCategory.CASUALTY):
            shift_stat(besieged, "population", -report.dead)
    if victor is not None:
        report.captives = await mass_captives(ctx, besieged, victor, siege.war_id if siege is not None else 0, depth.captive_pct) if siege is not None else 0
        report.relics = await plunder_relics(ctx, besieged, victor)
        report.witnesses = await infamy(ctx, besieged, victor, await RegionAtlas.load(ctx.session))
        await change_relation(ctx, besieged.id, victor.id, -ctx.rules.campaigns.conquest_relation, MemoryKind.CONQUERED_US, note="sacked the city")
    report.maimed = await maim(ctx, besieged)
    burn = depth.district_burn * (2 if choice is SackChoice.RAZE else 1)
    report.districts = await burn_districts(ctx, besieged, burn)
    ground = await region_environment(ctx.session, besieged.id)
    if ground is not None:
        await scar_region(ctx.session, ctx.rules, ground, ScarKind.BURNED, burn)
    morale = ctx.rules.morale
    for march in homeward:
        rows = await stacks_of(ctx.session, march.army.id)
        dishearten(rows, -morale.home_sacked_rage)
        desert(ctx.rules, march, rows, round_half_up((stat(march.army, "size") or 0) * morale.home_sacked_desertion_pct / PERCENT))
        sync(march.army, rows, ctx.rules)
    await damage_districts(ctx, besieged, DistrictHarm.SACK, 1.0)
    ctx.count("sacks")
    await record_sack(ctx, besieged, report.dead)
    ctx.count("sacked_images", len(await smash(ctx, besieged.id, ctx.rules.art.sack_chance, "broken by the army that sacked the city")))
    if victor is not None:
        await ctx.chronicle(
            ChronicleKind.WAR,
            SACK_TEXT[choice].format(victor=victor.name, city=besieged.name, dead=report.dead, captives=report.captives, relics=report.relics),
            template_key=f"war.sack.{choice.value}",
            entity_ids=(victor.id, besieged.id),
            feed_category=FeedCategory.WAR,
            place_entity_id=besieged.id,
        )
    return report


SACK_TEXT = {
    SackChoice.MERCY: "{victor} spared {city}.",
    SackChoice.SACK: "{victor} sacked {city}: {dead} died, {captives} were led away captive and {relics} treasures were carried off.",
    SackChoice.RAZE: "{victor} razed {city} to the ground: {dead} died, {captives} were enslaved and its districts burned.",
}
