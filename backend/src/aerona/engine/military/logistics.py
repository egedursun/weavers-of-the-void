from dataclasses import dataclass
from math import log2

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.military import ArmyMovementRow, ArmyProfileRow, ArmyUnitRow, CampaignFrontRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow, PolityTreasuryRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import ItemClass, Technique
from aerona.domain.enums.environment import MovementMode
from aerona.domain.enums.military import Stance
from aerona.domain.enums.mortal import HarshnessScale
from aerona.engine.context import TickContext
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.environment.perils import danger_toll, navigate
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.lore.research import has_technique
from aerona.engine.military.units import stacks_of, sync, take
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.harshness import harshness
from aerona.engine.primitives.levies import demobilise
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import set_stats, stat
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


def step_towards(rules: Rules, atlas: RegionAtlas, ground: EnvironmentBook, march: March, *, charted: bool = False, supplied: bool = False) -> int:
    profile = march.profile
    if march.goal is None or profile.region_entity_id is None or profile.region_entity_id == march.goal:
        return 0
    path = atlas.region_path(profile.region_entity_id, march.goal) or []
    reach = rules.logistics.march_regions + (rules.maps.march_regions if charted else 0) + (rules.technique_effects.logistics_regions if supplied else 0)
    if profile.forced_march:
        reach = round_half_up(reach * rules.logistics.forced_march_pct / PERCENT)
    moved = 0
    for region_id in path[1 : reach + 1]:
        if not passable(rules, ground.regions.get(region_id)):
            break
        profile.region_entity_id = region_id
        moved += 1
    return moved


def tire(rules: Rules, rows: list[ArmyUnitRow], profile: ArmyProfileRow) -> None:
    for row in rows:
        if profile.forced_march and profile.stance is Stance.MARCH:
            row.fatigue = clamp_int(row.fatigue + rules.logistics.forced_fatigue, 0, PERCENT)
        elif profile.stance in RESTING:
            row.fatigue = clamp_int(row.fatigue - rules.logistics.rest_fatigue, 0, PERCENT)


def entrench(rules: Rules, profile: ArmyProfileRow) -> None:
    if profile.stance in {Stance.ENTRENCH, Stance.GARRISON, Stance.BESIEGE}:
        profile.entrenchment = clamp_int(profile.entrenchment + rules.logistics.entrench_gain, 0, PERCENT)
    else:
        profile.entrenchment = 0


def supply_line(atlas: RegionAtlas, owner: EntityRow, profile: ArmyProfileRow) -> list[int]:
    home = atlas.top_region(owner.id)
    if home is None or profile.region_entity_id is None:
        return []
    return atlas.region_path(home, profile.region_entity_id) or []


def feed(ctx: TickContext, march: March, region: RegionEnvironmentRow | None, home: int | None, log: Season) -> int:
    table = ctx.rules.logistics
    profile = march.profile
    size = stat(march.army, "size") or 0
    if home is not None and profile.region_entity_id == home:
        profile.supply_days = table.supply_days
        return 0
    profile.supply_days = max(0, profile.supply_days - table.season_days)
    if region is None:
        return 0
    fed = max(1, region.farmed * table.supply_per_farmed)
    if profile.stance in {Stance.FORAGE, Stance.MARCH, Stance.BESIEGE, Stance.RAID}:
        profile.supply_days = min(table.supply_days, profile.supply_days + round_half_up(table.forage_days * min(1.0, fed / max(1, size))))
        region.harvest_pct = clamp_int(region.harvest_pct - table.forage_scar, 0, PERCENT)
    if size <= fed:
        return 0
    lost = round_half_up(size * table.over_supply_attrition_pct / PERCENT * log2(size / fed))
    log.dead += lost
    return lost


def raid_line(ctx: TickContext, march: March, line: list[int], log: Season) -> None:
    table = ctx.rules.logistics
    if len(line) - 1 < table.raid_line_length:
        return
    if ctx.rng(f"supply_raid.{march.army.id}.{ctx.epoch}.{len(line)}").chance(table.raid_line_chance):
        march.profile.supply_days //= 2
        log.raided = True


def camp_sickness(ctx: TickContext, march: March, region: RegionEnvironmentRow | None) -> int:
    table = ctx.rules.attrition
    profile = march.profile
    load = region.disease_load if region is not None else PERCENT // 2
    if profile.stance in RESTING:
        profile.disease = clamp_int(profile.disease + round_half_up(table.camp_disease_gain * load / PERCENT), 0, PERCENT)
    else:
        profile.disease = clamp_int(profile.disease - table.camp_disease_gain // 2, 0, PERCENT)
    return round_half_up((stat(march.army, "size") or 0) * table.disease_pct / PERCENT * profile.disease / PERCENT)


async def wages(ctx: TickContext, march: March) -> bool:
    cost = round_half_up((stat(march.army, "size") or 0) * ctx.rules.logistics.pay_per_100 / HUNDRED)
    profile = march.profile
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
    return paid >= cost


def desert(rules: Rules, march: March, rows: list[ArmyUnitRow], soldiers: int) -> int:
    soldiers = take(rows, soldiers)
    if soldiers <= 0:
        return 0
    size = stat(march.army, "size") or 0
    returned = demobilise(rules, march.owner, soldiers)
    with flowing(FlowCategory.LEVY):
        set_stats(march.army, size=max(0, size - returned))
    return soldiers


def dishearten(rows: list[ArmyUnitRow], loss: int) -> None:
    for row in rows:
        row.morale = clamp_int(row.morale - loss, 0, PERCENT)


async def holds_map(ctx: TickContext, owner_id: int) -> bool:
    owned = select(BondRow.target_node_id).where(BondRow.source_node_id == owner_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    found = await ctx.session.scalar(
        select(ItemProfileRow.item_entity_id).where(ItemProfileRow.item_entity_id.in_(owned), ItemProfileRow.item_class == ItemClass.MAP).limit(1)
    )
    return found is not None


async def campaign_season(ctx: TickContext, atlas: RegionAtlas, ground: EnvironmentBook, march: March, season: int) -> Season:
    log = Season()
    rows = await stacks_of(ctx.session, march.army.id)
    profile = march.profile
    origin = profile.region_entity_id
    charted = await holds_map(ctx, march.owner.id)
    supplied = await has_technique(ctx.session, march.owner.id, Technique.LOGISTICS)
    log.moved = 0 if "region_id" in profile.locked else step_towards(ctx.rules, atlas, ground, march, charted=charted, supplied=supplied)
    if "stance" in profile.locked:
        pass
    elif march.goal is not None and profile.region_entity_id == march.goal:
        profile.stance = Stance.BESIEGE if march.attacking else Stance.GARRISON
    elif not march.attacking:
        profile.stance = Stance.ENTRENCH
    wandering = await navigate(ctx, march.army, march.owner, profile.region_entity_id, origin, charted=charted)
    if wandering.lost and "region_id" not in profile.locked:
        profile.region_entity_id = origin
        log.moved = 0
    tire(ctx.rules, rows, profile)
    entrench(ctx.rules, profile)
    region = ground.regions.get(profile.region_entity_id) if profile.region_entity_id is not None else None
    line = supply_line(atlas, march.owner, profile)
    profile.supply_line = line
    raid_line(ctx, march, line, log)
    peril = await danger_toll(ctx, march.army, rows, profile.region_entity_id)
    dead = feed(ctx, march, region, atlas.top_region(march.owner.id), log) + camp_sickness(ctx, march, region) + wandering.dead + peril.dead
    attrition = ctx.rules.attrition
    size = stat(march.army, "size") or 0
    if profile.supply_days <= 0:
        log.starving = True
        dead += round_half_up(size * attrition.starvation_pct / PERCENT * harshness(ctx.rules, HarshnessScale.FAMINE_DEATH))
        dishearten(rows, round_half_up(ctx.rules.morale.base * ctx.rules.morale.supply_pct / PERCENT))
    log.unpaid = not await wages(ctx, march)
    if log.unpaid:
        dishearten(rows, ctx.rules.logistics.unpaid_morale)
    if log.starving or log.unpaid:
        log.deserted = desert(ctx.rules, march, rows, round_half_up(size * attrition.desertion_pct / PERCENT))
    log.dead = take(rows, dead)
    sync(march.army, rows, ctx.rules)
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
                    ("lost", wandering.lost),
                    ("ambushed", peril.ambushed),
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
    return row
