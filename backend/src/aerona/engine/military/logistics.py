from dataclasses import dataclass
from math import log2

from sqlalchemy import select

from aerona.catalog.units import UNITS
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow, WorldSeasonRow
from aerona.db.tables.military import ArmyMovementRow, ArmyProfileRow, ArmyUnitRow, CampaignFrontRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow, PolityTreasuryRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import ItemClass, Technique
from aerona.domain.enums.environment import MovementMode, ScarKind, WeatherKind
from aerona.domain.enums.military import MoraleState, MutinyOutcome, Stance
from aerona.engine.context import TickContext
from aerona.engine.environment.book import EnvironmentBook, add_scar
from aerona.engine.environment.perils import Wandering, danger_toll, navigate
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.lore.research import has_technique
from aerona.engine.military.campaign import (
    babel,
    carry,
    choose_stance,
    class_desertion,
    feed_mounts,
    loot_wages,
    march_budget,
    mutiny,
    mutiny_pressure,
    on_road,
    plunder,
    quartermaster,
    raid_supply,
    retreat,
    sanitation_of,
    scorch,
    size_of,
    step_cost,
    straggle,
    summer,
)
from aerona.engine.military.command import command_areas, thrift
from aerona.engine.military.engineering import engineer, engineers, leave_earthworks, supply_limit
from aerona.engine.military.finance import war_credit
from aerona.engine.military.units import rearm, stacks_of, sync, take
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.levies import demobilise
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.relations.book import ensure_relation, shift
from aerona.rules.registry import Rules

HUNDRED = 100
RESTING = frozenset({Stance.ENTRENCH, Stance.GARRISON, Stance.BESIEGE})


@dataclass
class Season:
    moved: int = 0
    dead: int = 0
    deserted: int = 0
    raided: bool = False
    starving: bool = False
    unpaid: bool = False
    foraged: bool = False
    scorched: bool = False
    unfed_mounts: bool = False
    mutiny: MutinyOutcome | None = None
    rejoined: int = 0
    eaten_out: bool = False
    works: str | None = None


@dataclass(frozen=True)
class March:
    army: EntityRow
    owner: EntityRow
    profile: ArmyProfileRow
    goal: int | None
    attacking: bool


def passable(rules: Rules, region: RegionEnvironmentRow | None) -> bool:
    if region is None:
        return True
    return region.passability.get(MovementMode.ON_FOOT.value, PERCENT) >= rules.logistics.passability_floor


def step_towards(
    rules: Rules,
    atlas: RegionAtlas,
    ground: EnvironmentBook,
    march: March,
    *,
    charted: bool = False,
    supplied: bool = False,
    weather: WeatherKind | None = None,
    season: WorldSeasonRow | None = None,
    pontoon: bool = False,
) -> int:
    profile = march.profile
    if march.goal is None or profile.region_entity_id is None or profile.region_entity_id == march.goal:
        return 0
    path = atlas.region_path(profile.region_entity_id, march.goal) or []
    reach = rules.logistics.march_regions + (rules.maps.march_regions if charted else 0) + (rules.technique_effects.logistics_regions if supplied else 0)
    if profile.forced_march:
        reach = round_half_up(reach * rules.logistics.forced_march_pct / PERCENT)
    here = ground.regions.get(profile.region_entity_id)
    budget = march_budget(rules, reach, weather=weather, season=season, road=on_road(here, rules), baggage=profile.baggage)
    moved = 0
    for region_id in path[1:]:
        region = ground.regions.get(region_id)
        cost = step_cost(rules, region, season, pontoon=pontoon)
        if not passable(rules, region) or cost > budget:
            break
        budget -= cost
        profile.region_entity_id = region_id
        moved += 1
    return moved


def tire(rules: Rules, rows: list[ArmyUnitRow], profile: ArmyProfileRow) -> None:
    for row in rows:
        if profile.forced_march and profile.stance is Stance.MARCH:
            row.fatigue = clamp_int(row.fatigue + rules.logistics.forced_fatigue, 0, PERCENT)
        elif profile.stance in RESTING:
            row.fatigue = clamp_int(row.fatigue - rules.logistics.rest_fatigue, 0, PERCENT)


def regroup(rules: Rules, rows: list[ArmyUnitRow], profile: ArmyProfileRow) -> int:
    table = rules.battle_depth
    rested = table.organisation_rest if profile.stance in RESTING else round(table.organisation_rest * table.march_rest_pct / PERCENT)
    if profile.supply_days <= 0:
        rested = 0
    returned = 0
    for row in rows:
        if "organisation" not in row.locked:
            loss = table.forced_march_organisation if profile.forced_march and profile.stance is Stance.MARCH else 0
            row.organisation = clamp_int(row.organisation + rested - loss, 0, PERCENT)
        if "ammunition" not in row.locked and UNITS[row.kind].missile > 0 and profile.baggage > 0:
            row.ammunition = min(table.volleys_carried, row.ammunition + table.resupply_volleys)
        if row.missing > 0 and "missing" not in row.locked:
            back = round_half_up(row.missing * table.rejoin_pct / PERCENT)
            row.count += back
            returned += back
            row.missing = 0
        if "morale_state" not in row.locked:
            row.morale_state = MoraleState.STEADY if row.morale >= rules.morale.rout_morale else MoraleState.WAVERING
    return returned


def entrench(rules: Rules, profile: ArmyProfileRow, left: RegionEnvironmentRow | None = None) -> None:
    if profile.stance in {Stance.ENTRENCH, Stance.GARRISON, Stance.BESIEGE}:
        profile.entrenchment = clamp_int(profile.entrenchment + rules.logistics.entrench_gain, 0, PERCENT)
    else:
        if left is not None and not held(left.entity_id):
            leave_earthworks(rules, profile, left)
        profile.entrenchment = 0


def supply_line(atlas: RegionAtlas, owner: EntityRow, profile: ArmyProfileRow) -> list[int]:
    home = atlas.top_region(owner.id)
    if home is None or profile.region_entity_id is None:
        return []
    return atlas.region_path(home, profile.region_entity_id) or []


def feed(
    ctx: TickContext,
    march: March,
    region: RegionEnvironmentRow | None,
    home: int | None,
    log: Season,
    *,
    season: WorldSeasonRow | None = None,
    thrift: float = 1.0,
) -> int:
    table = ctx.rules.logistics
    profile = march.profile
    size = stat(march.army, "size") or 0
    if home is not None and profile.region_entity_id == home:
        profile.supply_days = table.supply_days
        return 0
    profile.supply_days = max(0, profile.supply_days - round_half_up(table.season_days * thrift))
    if region is None:
        return 0
    fed = supply_limit(ctx.rules, region, season)
    if profile.stance in {Stance.FORAGE, Stance.MARCH, Stance.BESIEGE, Stance.RAID}:
        profile.supply_days = min(table.supply_days, profile.supply_days + round_half_up(table.forage_days * min(1.0, fed / max(1, size))))
        region.harvest_pct = clamp_int(region.harvest_pct - table.forage_scar, 0, PERCENT)
        log.foraged = True
        if profile.stance in {Stance.FORAGE, Stance.RAID} or march.attacking:
            plunder(ctx.rules, region)
    if size <= fed:
        return 0
    log.eaten_out = True
    lost = round_half_up(size * table.over_supply_attrition_pct / PERCENT * log2(size / fed))
    log.dead += lost
    return lost


async def eat_out(ctx: TickContext, atlas: RegionAtlas, march: March, region: RegionEnvironmentRow | None) -> int:
    if region is None:
        return 0
    table = ctx.rules.army_depth
    if not held(region.entity_id):
        add_scar(region, ScarKind.PLUNDERED, table.oversupply_scar)
    soured = 0
    for community_id in atlas.communities_in(region.entity_id):
        if community_id == march.owner.id or held(community_id):
            continue
        view = await ensure_relation(ctx.session, community_id, march.owner.id, ctx.epoch)
        if view is None:
            continue
        shift(ctx.rules, view, ctx.epoch, friendship=-table.oversupply_resentment)
        soured += 1
    return soured


def raid_line(ctx: TickContext, march: March, line: list[int], log: Season) -> None:
    table = ctx.rules.logistics
    if len(line) - 1 < table.raid_line_length:
        return
    if ctx.rng(f"supply_raid.{march.army.id}.{ctx.epoch}.{len(line)}").chance(table.raid_line_chance):
        march.profile.supply_days //= 2
        log.raided = True


def camp_sickness(ctx: TickContext, march: March, region: RegionEnvironmentRow | None, *, sanitation: int = 0, fever: bool = False) -> int:
    table = ctx.rules.attrition
    depth = ctx.rules.campaign_depth
    profile = march.profile
    load = region.disease_load if region is not None else PERCENT // 2
    kept = 1 - depth.sanitation_pct / PERCENT * sanitation / PERCENT
    if profile.stance in RESTING:
        gain = table.camp_disease_gain * load / PERCENT * kept + (depth.summer_fever if fever else 0)
        profile.disease = clamp_int(profile.disease + round_half_up(gain), 0, PERCENT)
    elif fever:
        profile.disease = clamp_int(profile.disease + depth.summer_fever // 2, 0, PERCENT)
    else:
        profile.disease = clamp_int(profile.disease - table.camp_disease_gain // 2, 0, PERCENT)
    return round_half_up((stat(march.army, "size") or 0) * table.disease_pct / PERCENT * profile.disease / PERCENT)


async def wages(ctx: TickContext, march: March, rows: list[ArmyUnitRow] | None = None) -> bool:
    cost = round_half_up((stat(march.army, "size") or 0) * ctx.rules.logistics.pay_per_100 / HUNDRED)
    profile = march.profile
    cost -= await loot_wages(ctx, march.owner, profile, cost, rows or [])
    paid = min(profile.war_chest, cost)
    profile.war_chest -= paid
    cost -= paid
    if cost <= 0:
        return True
    polity_id = await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == march.owner.id).limit(1))
    if polity_id is None:
        return True
    realm = await ctx.session.get(PolityProfileRow, polity_id)
    if realm is None:
        return True
    taxed = await ctx.session.scalar(select(PolityTreasuryRow.id).where(PolityTreasuryRow.polity_entity_id == polity_id, PolityTreasuryRow.amount > 0).limit(1))
    if taxed is None and realm.war_chest <= 0 and realm.treasury <= 0:
        return True
    paid = min(realm.war_chest, cost)
    realm.war_chest -= paid
    cost -= paid
    paid = min(max(0, realm.treasury), cost)
    realm.treasury -= paid
    cost -= paid
    if cost > 0 and await war_credit(ctx, march.owner, realm, polity_id):
        paid = min(realm.war_chest, cost)
        realm.war_chest -= paid
        cost -= paid
    return cost <= 0


def desert(rules: Rules, march: March, rows: list[ArmyUnitRow], soldiers: int) -> int:
    soldiers = take(rows, soldiers)
    if soldiers <= 0:
        return 0
    size = stat(march.army, "size") or 0
    returned = demobilise(rules, march.owner, soldiers)
    with flowing(FlowCategory.LEVY):
        set_stats(march.army, size=max(0, size - returned))
    return soldiers


async def desert_by_class(ctx: TickContext, march: March, rows: list[ArmyUnitRow]) -> int:
    await babel(ctx, march.profile, rows)
    leaving = await class_desertion(ctx, march.owner, march.profile, rows)
    if leaving <= 0:
        return 0
    returned = demobilise(ctx.rules, march.owner, leaving)
    with flowing(FlowCategory.LEVY):
        set_stats(march.army, size=max(0, (stat(march.army, "size") or 0) - returned))
    return leaving


def dishearten(rows: list[ArmyUnitRow], loss: int) -> None:
    for row in rows:
        row.morale = clamp_int(row.morale - loss, 0, PERCENT)


async def holds_map(ctx: TickContext, owner_id: int) -> bool:
    owned = select(BondRow.target_node_id).where(BondRow.source_node_id == owner_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    found = await ctx.session.scalar(
        select(ItemProfileRow.item_entity_id).where(ItemProfileRow.item_entity_id.in_(owned), ItemProfileRow.item_class == ItemClass.MAP).limit(1)
    )
    return found is not None


async def hardship(ctx: TickContext, march: March, rows: list[ArmyUnitRow], log: Season) -> int:
    attrition = ctx.rules.attrition
    profile = march.profile
    size = stat(march.army, "size") or 0
    dead = 0
    if profile.supply_days <= 0:
        log.starving = True
        dead += round_half_up(size * attrition.starvation_pct / PERCENT)
        dishearten(rows, round_half_up(ctx.rules.morale.base * ctx.rules.morale.supply_pct / PERCENT))
    log.unpaid = not await wages(ctx, march, rows)
    if log.unpaid:
        dishearten(rows, ctx.rules.logistics.unpaid_morale)
    if log.starving or log.unpaid:
        log.deserted = await desert_by_class(ctx, march, rows)
    dead += straggle(ctx.rules, rows, profile)
    mutiny_pressure(ctx.rules, profile, hungry=log.starving, unpaid=log.unpaid)
    return dead


async def plan_stance(ctx: TickContext, march: March, enemy: March | None) -> None:
    profile = march.profile
    row = await ctx.session.get(ArmyRow, march.army.id)
    if "stance" in profile.locked or row is None:
        return
    at_goal = march.goal is not None and profile.region_entity_id == march.goal
    outnumbered = enemy is not None and size_of(enemy.army) * 2 > size_of(march.army) * 3
    profile.stance = await choose_stance(ctx, march.owner, row, profile, attacking=march.attacking, at_goal=at_goal, outnumbered=outnumbered)


async def advance(
    ctx: TickContext,
    atlas: RegionAtlas,
    ground: EnvironmentBook,
    march: March,
    *,
    rows: list[ArmyUnitRow],
    log: Season,
    left: RegionEnvironmentRow | None,
    weather: WeatherKind | None,
    season_row: WorldSeasonRow | None,
    enemy: March | None,
) -> Wandering:
    profile = march.profile
    origin = profile.region_entity_id
    charted = await holds_map(ctx, march.owner.id)
    supplied = await has_technique(ctx.session, march.owner.id, Technique.LOGISTICS)
    await plan_stance(ctx, march, enemy)
    if profile.stance is Stance.RETREAT:
        log.works = engineer(ctx.rules, profile, rows, left) if left is not None and not held(left.entity_id) else None
        log.moved = retreat(ctx.rules, atlas, march.owner, profile)
    elif "region_id" not in profile.locked and profile.stance not in RESTING:
        pontoon = engineers(ctx.rules, rows)
        log.moved = step_towards(ctx.rules, atlas, ground, march, charted=charted, supplied=supplied, weather=weather, season=season_row, pontoon=pontoon)
    if enemy is not None:
        log.raided = raid_supply(ctx.rules, profile, enemy.profile) > 0 or log.raided
    wandering = await navigate(ctx, march.army, march.owner, profile.region_entity_id, origin, charted=charted)
    if wandering.lost and "region_id" not in profile.locked:
        profile.region_entity_id = origin
        log.moved = 0
    return wandering


async def campaign_season(
    ctx: TickContext,
    atlas: RegionAtlas,
    ground: EnvironmentBook,
    march: March,
    season: int,
    *,
    weather: WeatherKind | None = None,
    season_row: WorldSeasonRow | None = None,
    enemy: March | None = None,
) -> Season:
    log = Season()
    rows = await stacks_of(ctx.session, march.army.id)
    profile = march.profile
    origin = profile.region_entity_id
    command = await ctx.session.get(ArmyRow, march.army.id)
    areas = await command_areas(ctx.session, command.commander_entity_id if command is not None else None)
    left = ground.regions.get(origin) if origin is not None else None
    wandering = await advance(ctx, atlas, ground, march, rows=rows, log=log, left=left, weather=weather, season_row=season_row, enemy=enemy)
    tire(ctx.rules, rows, profile)
    log.rejoined = regroup(ctx.rules, rows, profile)
    entrench(ctx.rules, profile, left if log.moved else None)
    region = ground.regions.get(profile.region_entity_id) if profile.region_entity_id is not None else None
    if profile.stance is not Stance.RETREAT and region is not None and not held(region.entity_id):
        log.works = engineer(ctx.rules, profile, rows, region)
    home = atlas.top_region(march.owner.id)
    if not march.attacking and enemy is not None and region is not None and profile.region_entity_id == home:
        army_row = await ctx.session.get(ArmyRow, march.army.id)
        if army_row is not None and await scorch(ctx, march.owner, army_row, region):
            log.scorched = True
    line = supply_line(atlas, march.owner, profile)
    profile.supply_line = line
    raid_line(ctx, march, line, log)
    profile.supply_days += await quartermaster(ctx, march.army.id)
    sanitation = await sanitation_of(ctx, march.owner)
    fever = summer(season_row, ground.seasons_of(march.owner.world_id))
    peril = await danger_toll(ctx, march.army, rows, profile.region_entity_id)
    dead = feed(ctx, march, region, home, log, season=season_row, thrift=thrift(ctx.rules, areas)) + camp_sickness(
        ctx, march, region, sanitation=sanitation, fever=fever
    )
    if log.eaten_out:
        await eat_out(ctx, atlas, march, region)
    dead += wandering.dead + peril.dead
    log.unfed_mounts = not feed_mounts(ctx.rules, profile, rows, log.foraged)
    await rearm(ctx, march.army, march.owner, rows)
    dead += await hardship(ctx, march, rows, log)
    log.dead = take(rows, dead)
    sync(march.army, rows, ctx.rules)
    carry(ctx.rules, profile, stat(march.army, "size") or 0)
    army_row = await ctx.session.get(ArmyRow, march.army.id)
    if army_row is not None:
        log.mutiny = await mutiny(ctx, march.army, army_row, profile, enemy_id=enemy.owner.id if enemy is not None else None)
    profile.updated_epoch = ctx.epoch
    ctx.session.add(
        ArmyMovementRow(
            army_entity_id=march.army.id,
            epoch=ctx.epoch,
            season=season,
            from_region_id=origin,
            to_region_id=profile.region_entity_id,
            stance=profile.stance,
            supply_days=profile.supply_days,
            attrition=log.dead + log.deserted,
            note=", ".join(
                word
                for word, hit in (
                    ("raided", log.raided),
                    ("starving", log.starving),
                    ("unpaid", log.unpaid),
                    ("scorched", log.scorched),
                    ("mounts unfed", log.unfed_mounts),
                    ("mutiny", log.mutiny is not None),
                    ("lost", wandering.lost),
                    ("ambushed", peril.ambushed),
                    ("eaten out", log.eaten_out),
                    (log.works or "", log.works is not None),
                )
                if hit
            )
            or None,
        )
    )
    return log


def in_contact(atlas: RegionAtlas, first: ArmyProfileRow, second: ArmyProfileRow) -> bool:
    if first.region_entity_id is None or second.region_entity_id is None:
        return True
    hops = atlas.region_hops(first.region_entity_id, second.region_entity_id)
    return hops is None or hops <= 1


async def mark_front(ctx: TickContext, war_id: int, first: ArmyProfileRow, second: ArmyProfileRow) -> CampaignFrontRow | None:
    if first.region_entity_id is None or second.region_entity_id is None:
        return None
    pair = sorted((first.region_entity_id, second.region_entity_id))
    query = select(CampaignFrontRow).where(CampaignFrontRow.war_id == war_id, CampaignFrontRow.first_region_id == pair[0])
    row = await ctx.session.scalar(query.where(CampaignFrontRow.second_region_id == pair[1]))
    if row is None:
        row = CampaignFrontRow(war_id=war_id, first_region_id=pair[0], second_region_id=pair[1], since_epoch=ctx.epoch, last_epoch=ctx.epoch)
        ctx.session.add(row)
        await ctx.session.flush()
    row.last_epoch = ctx.epoch
    for profile in (first, second):
        if not held(profile.army_entity_id) and "contact_seasons" not in profile.locked:
            profile.contact_seasons += 1
    return row
