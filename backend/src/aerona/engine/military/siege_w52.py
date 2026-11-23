from typing import Protocol

from sqlalchemy import select

from aerona.catalog.units import UNITS
from aerona.catalog.war_w52 import (
    BREACHING_WORKS,
    COVERING_WORKS,
    DEFENCES,
    ENCIRCLING_WORKS,
    FALL_CHOICES,
    SIEGE_ACTION_SPECS,
    SIEGE_WORKS,
    SPECIAL_WORKS,
    WALL_TOP_WORKS,
)
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.intrigue import HookRow
from aerona.db.tables.military import ArmyProfileRow, CaptiveCohortRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.settlement import SettlementInfrastructureRow, SettlementProfileRow
from aerona.db.tables.warfare import SiegeRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.environment import ScarKind
from aerona.domain.enums.military import CaptiveFate, DefenderAction, SackChoice, SiegeAction, SiegeWork, UnitKind
from aerona.domain.enums.mind import ActKind, MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.settlement import WaterSupply
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import coin_of, receive_coin, take_coin
from aerona.engine.environment.book import add_scar
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.lore.research import has_technique
from aerona.engine.military.engineering import RIVERS
from aerona.engine.military.units import stacks_of
from aerona.engine.mind.hooks import judged
from aerona.engine.primitives.levies import add_heads, levies_from
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.recording.record import record
from aerona.engine.services.community_relations import change_relation


class Besieging(Protocol):
    @property
    def army(self) -> EntityRow: ...

    @property
    def owner(self) -> EntityRow: ...

    @property
    def profile(self) -> ArmyProfileRow: ...


def pace(ctx: TickContext, work: SiegeWork) -> int:
    return round_half_up(ctx.rules.siege_depth.work_progress * int(getattr(ctx.rules.siege, SIEGE_WORKS[work].labour_rule)) / PERCENT)


def strength(ctx: TickContext, work: SiegeWork) -> int:
    return int(getattr(ctx.rules.siege, SIEGE_WORKS[work].effect_rule))


def finished(siege: SiegeRow, work: SiegeWork) -> bool:
    return int((siege.works or {}).get(work.value, 0)) >= PERCENT


def progress(ctx: TickContext, siege: SiegeRow, works: list[SiegeWork]) -> list[SiegeWork]:
    built = dict(siege.works or {})
    done: list[SiegeWork] = []
    for work in works:
        before = int(built.get(work.value, 0))
        built[work.value] = min(PERCENT, before + pace(ctx, work))
        if before < PERCENT <= built[work.value]:
            done.append(work)
    siege.works = built
    return done


async def capable(ctx: TickContext, siege: SiegeRow, march: Besieging, engines: float) -> frozenset[SiegeWork]:
    rows = await stacks_of(ctx.session, march.army.id)
    kinds = {row.kind for row in rows if row.count > 0}
    found = {work for work, spec in SIEGE_WORKS.items() if not (spec.needs_flight or spec.needs_network or spec.needs_rites)}
    if engines <= 0:
        found.discard(SiegeWork.BOMBARDMENT)
    if any(UNITS[kind].flying for kind in kinds):
        found.add(SiegeWork.AIR_ASSAULT)
    if kinds & {UnitKind.BATTLE_CASTERS, UnitKind.SUPPORT_CASTERS}:
        found.add(SiegeWork.RITE_BREACH)
    if await has_technique(ctx.session, march.owner.id, Technique.COMPUTATION) and await has_technique(
        ctx.session, siege.besieged_entity_id, Technique.COMPUTATION
    ):
        found.add(SiegeWork.NETWORK_ATTACK)
    return frozenset(found)


async def raise_works(ctx: TickContext, siege: SiegeRow, action: SiegeAction, march: Besieging, engines: float) -> list[SiegeWork]:
    able = await capable(ctx, siege, march, engines)
    wanted = [work for work in SIEGE_ACTION_SPECS[action].works if work in able]
    if SIEGE_ACTION_SPECS[action].batters or action is SiegeAction.ASSAULT:
        wanted += [work for work in SPECIAL_WORKS if work in able]
    done = progress(ctx, siege, wanted)
    for work in done:
        await record(
            ctx,
            "siege.work_built",
            roles={IncidentRole.ACTOR: siege.besieger_entity_id, IncidentRole.TARGET: siege.besieged_entity_id},
            facts={"work": work},
            place=siege.besieged_entity_id,
        )
    return done


def breach_from_works(ctx: TickContext, siege: SiegeRow) -> float:
    return sum(strength(ctx, work) for work in BREACHING_WORKS | WALL_TOP_WORKS if finished(siege, work)) / PERCENT


def hunger_from_works(ctx: TickContext, siege: SiegeRow, eaten: int) -> int:
    extra = sum(strength(ctx, work) for work in ENCIRCLING_WORKS if finished(siege, work))
    return round_half_up(eaten * (PERCENT + extra) / PERCENT)


def sapped(ctx: TickContext, siege: SiegeRow, lost: int) -> int:
    cover = sum(strength(ctx, work) for work in COVERING_WORKS if finished(siege, work))
    return round_half_up(lost * max(0, PERCENT - cover) / PERCENT)


def undo_mines(ctx: TickContext, works: dict[str, int]) -> None:
    mined = int(works.get(SiegeWork.MINES.value, 0))
    works[SiegeWork.MINES.value] = max(0, mined - round_half_up(mined * strength(ctx, SiegeWork.COUNTERMINES) / PERCENT))


async def inside_grudge(ctx: TickContext, siege: SiegeRow) -> bool:
    town = siege.besieged_entity_id
    factions = select(FactionProfileRow.faction_entity_id).where(FactionProfileRow.home_entity_id == town)
    grudge = await ctx.session.scalar(
        select(MemoryRow.id).where(MemoryRow.holder_node_id.in_(factions), MemoryRow.subject_node_id == town, MemoryRow.magnitude < 0).limit(1)
    )
    if grudge is not None:
        return True
    hook = await ctx.session.scalar(select(HookRow.id).where(HookRow.holder_node_id == siege.besieger_entity_id, HookRow.target_node_id.in_(factions)).limit(1))
    return hook is not None


async def can_suborn(ctx: TickContext, siege: SiegeRow) -> bool:
    besieger = await living_entity(ctx.session, siege.besieger_entity_id)
    if besieger is None or siege.breaches > 0:
        return False
    return await inside_grudge(ctx, siege) and await coin_of(ctx.session, ctx.rules, besieger) >= ctx.rules.siege.suborn_cost


async def suborn(ctx: TickContext, siege: SiegeRow, walls: SettlementInfrastructureRow | None) -> bool:
    table = ctx.rules.siege
    besieger = await living_entity(ctx.session, siege.besieger_entity_id)
    if besieger is None or held(siege.besieged_entity_id) or not await take_coin(ctx.session, ctx.rules, besieger, table.suborn_cost):
        return False
    chance = table.suborn_base_pct + (table.suborn_grudge_bonus_pct if await inside_grudge(ctx, siege) else 0)
    roles = {IncidentRole.ACTOR: besieger.id, IncidentRole.TARGET: siege.besieged_entity_id}
    if ctx.rng(f"suborn.{siege.id}.{siege.rounds}").chance(chance):
        if "breaches" not in siege.locked:
            siege.breaches += 1
        await record(ctx, "siege.gate_betrayed", roles=roles, facts={"breaches": siege.breaches}, place=siege.besieged_entity_id)
        return True
    if walls is not None and "walls_condition" not in (walls.locked or []):
        walls.walls_condition = clamp_int(walls.walls_condition + table.suborn_harden, 0, PERCENT)
    town = await ctx.session.get(SettlementProfileRow, siege.besieged_entity_id)
    if town is not None and "public_order" not in town.locked:
        town.public_order = clamp_int(town.public_order + table.suborn_harden, 0, PERCENT)
    await record(ctx, "siege.plot_exposed", roles=roles, facts={"hardened": table.suborn_harden}, place=siege.besieged_entity_id)
    return False


async def ground_of(ctx: TickContext, town_id: int) -> RegionEnvironmentRow | None:
    town = await ctx.session.get(EntityRow, town_id)
    return await ctx.session.get(RegionEnvironmentRow, town.location_id) if town is not None and town.location_id is not None else None


async def floodable(ctx: TickContext, town_id: int, walls: SettlementInfrastructureRow | None) -> bool:
    ground = await ground_of(ctx, town_id)
    return (ground is not None and ground.river_class in RIVERS) or (walls is not None and walls.water is WaterSupply.AQUEDUCT)


def ordered(ctx: TickContext, siege: SiegeRow) -> bool:
    return siege.ordered_epoch is not None and siege.ordered_epoch >= ctx.epoch - 1


async def harsh_defence(ctx: TickContext, siege: SiegeRow, march: Besieging, walls: SettlementInfrastructureRow | None) -> DefenderAction | None:
    if siege.last_defence is not None and ("last_defence" in siege.locked or ordered(ctx, siege)):
        return siege.last_defence if not DEFENCES[siege.last_defence].needs_water or await floodable(ctx, siege.besieged_entity_id, walls) else None
    building = any(0 < int(value) < PERCENT for key, value in (siege.works or {}).items() if key != "famine")
    if building and await floodable(ctx, siege.besieged_entity_id, walls):
        return DefenderAction.FLOOD_APPROACHES
    if march.profile.supply_days < ctx.rules.logistics.season_days and siege.supplies >= ctx.rules.urban.ration_supplies_days:
        return DefenderAction.SCORCHED_EARTH
    if siege.supplies < ctx.rules.siegecraft.famine_days:
        return DefenderAction.EXPEL_MOUTHS
    return None


async def flood(ctx: TickContext, siege: SiegeRow) -> int:
    table = ctx.rules.siege
    built = dict(siege.works or {})
    halted = 0
    for work in SiegeWork:
        value = int(built.get(work.value, 0))
        if 0 < value < PERCENT:
            cut = round_half_up(value * table.flood_halt_pct / PERCENT)
            built[work.value] = value - cut
            halted += cut
    siege.works = built
    ground = await ground_of(ctx, siege.besieged_entity_id)
    if ground is not None and not held(ground.entity_id):
        ground.harvest_pct = clamp_int(ground.harvest_pct - table.flood_field_harm, 0, PERCENT)
    return halted


async def scorch(ctx: TickContext, siege: SiegeRow, march: Besieging) -> int:
    table = ctx.rules.siege
    ground = await ground_of(ctx, siege.besieged_entity_id)
    if ground is not None and not held(ground.entity_id):
        ground.harvest_pct = clamp_int(ground.harvest_pct - table.scorch_forage_cut_pct, 0, PERCENT)
        add_scar(ground, ScarKind.BURNED, table.scorch_forage_cut_pct // 2)
    cut = round_half_up(march.profile.supply_days * table.scorch_forage_cut_pct / PERCENT)
    if "supply_days" not in march.profile.locked:
        march.profile.supply_days = max(0, march.profile.supply_days - cut)
    return cut


async def expel(ctx: TickContext, siege: SiegeRow, besieged: EntityRow) -> int:
    table = ctx.rules.siege
    population = stat(besieged, "population") or 0
    driven = round_half_up(population * table.expel_share_pct / PERCENT)
    if driven <= 0:
        return 0
    with flowing(FlowCategory.MIGRATION):
        shift_stat(besieged, "population", -driven)
    if "supplies" not in siege.locked:
        siege.supplies += round_half_up(siege.supplies * table.expel_food_gain_pct / PERCENT)
    let_through = ctx.rng(f"expel.{siege.id}.{siege.rounds}").chance(table.expel_let_through_pct)
    survivors = driven if let_through else driven - round_half_up(driven * table.expel_lost_pct / PERCENT)
    home = await living_entity(ctx.session, besieged.affiliated_entity_id) if besieged.affiliated_entity_id is not None else None
    if home is not None and levies_from(home) and survivors > 0:
        add_heads(ctx.rules, home, survivors, FlowCategory.MIGRATION)
    await judged(ctx, besieged.id, besieged.id, ActKind.ABANDONING_ELDERS, note="drove out those who could not fight")
    return driven


async def defend(ctx: TickContext, siege: SiegeRow, besieged: EntityRow, march: Besieging, defence: DefenderAction) -> int:
    if defence is DefenderAction.FLOOD_APPROACHES:
        amount = await flood(ctx, siege)
    elif defence is DefenderAction.SCORCHED_EARTH:
        amount = await scorch(ctx, siege, march)
    elif defence is DefenderAction.EXPEL_MOUTHS:
        amount = await expel(ctx, siege, besieged)
    else:
        return 0
    await record(
        ctx,
        "siege.defence",
        roles={IncidentRole.ACTOR: besieged.id, IncidentRole.OPPONENT: siege.besieger_entity_id},
        facts={"defence": defence, "amount": amount},
        place=besieged.id,
    )
    return amount


async def fall_choice(ctx: TickContext, siege: SiegeRow, victor: EntityRow, choice: SackChoice, *, bondage: bool) -> SackChoice:
    if not FALL_CHOICES[choice].plunders or FALL_CHOICES[choice].razes or ("choice" in siege.locked and siege.choice is not None):
        return choice
    table = ctx.rules.sack
    town = await ctx.session.get(SettlementProfileRow, siege.besieged_entity_id)
    rng = ctx.rng(f"fall.{siege.id}")
    if town is not None and town.treasury >= table.ransom_from and rng.chance(table.ransom_pick_pct):
        return SackChoice.RANSOM_CITY
    if bondage and rng.chance(table.deport_pick_pct):
        return SackChoice.DEPORT
    return choice


async def ransom_city(ctx: TickContext, besieged: EntityRow, victor: EntityRow) -> int:
    table = ctx.rules.sack
    town = await ctx.session.get(SettlementProfileRow, besieged.id)
    paid = 0
    if town is not None and "treasury" not in town.locked and town.treasury > 0:
        paid = round_half_up(town.treasury * table.ransom_share_pct / PERCENT)
        town.treasury -= paid
    wealth = stat(besieged, "wealth")
    if wealth is not None:
        shift_stat(besieged, "wealth", -round_half_up(wealth * table.ransom_share_pct / PERCENT))
    await receive_coin(ctx.session, ctx.rules, victor, paid)
    await change_relation(ctx, besieged.id, victor.id, ctx.rules.siege_depth.infamy // 2, MemoryKind.GOODWILL, note="spared the city for a ransom")
    await record(ctx, "war.sack.ransom_city", roles={IncidentRole.ACTOR: victor.id, IncidentRole.TARGET: besieged.id}, facts={"paid": paid}, place=besieged.id)
    return paid


async def deport(ctx: TickContext, besieged: EntityRow, victor: EntityRow, war_id: int) -> int:
    table = ctx.rules.sack
    population = stat(besieged, "population") or 0
    moved = round_half_up(population * table.deport_share_pct / PERCENT)
    if moved <= 0:
        return 0
    with flowing(FlowCategory.CAPTIVE):
        shift_stat(besieged, "population", -moved)
    ctx.session.add(
        CaptiveCohortRow(
            captor_entity_id=victor.id,
            origin_entity_id=besieged.id,
            war_id=war_id,
            count=moved,
            social_class=SocialClass.FARMER,
            fate=CaptiveFate.LABOUR,
            since_epoch=ctx.epoch,
            settled_epoch=ctx.epoch,
        )
    )
    if levies_from(victor) and victor.status is EntityStatus.CANON:
        add_heads(ctx.rules, victor, moved, FlowCategory.CAPTIVE)
    await change_relation(ctx, besieged.id, victor.id, -ctx.rules.campaigns.conquest_relation, MemoryKind.CONQUERED_US, note="took its people away")
    await record(ctx, "war.sack.deport", roles={IncidentRole.ACTOR: victor.id, IncidentRole.TARGET: besieged.id}, facts={"moved": moved}, place=besieged.id)
    return moved
