from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyProfileRow, OccupationRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.warfare import ArmyRow, WarRow, WarSideRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.folkways import BiasedDecision
from aerona.domain.enums.mind import MemoryKind, ValueAxis
from aerona.domain.enums.war import WarStatus
from aerona.engine.context import TickContext
from aerona.engine.folkways.biases import lean_community
from aerona.engine.military.aims import REGION_AIMS, advance
from aerona.engine.military.logistics import March
from aerona.engine.military.support import peace_pressure
from aerona.engine.military.units import stacks_of, sync, take
from aerona.engine.mind.book import values_for
from aerona.engine.mind.space import value_distance
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import shift_stat, stat

ATROCITIES = (MemoryKind.KILLED_KIN, MemoryKind.FOUGHT_US)
ATROCITY_SCALE = 10
THOUSAND = 1000
HUNDRED = 100


async def resistance(ctx: TickContext, occupier: EntityRow, locals_id: int) -> int:
    table = ctx.rules.occupation
    distance = value_distance(await values_for(ctx.session, occupier.id), await values_for(ctx.session, locals_id))
    grief = await ctx.session.scalar(
        select(func.coalesce(func.sum(MemoryRow.magnitude), 0)).where(
            MemoryRow.holder_node_id == locals_id, MemoryRow.subject_node_id == occupier.id, MemoryRow.kind.in_(ATROCITIES), MemoryRow.magnitude < 0
        )
    )
    atrocity = min(PERCENT, -int(grief or 0) // ATROCITY_SCALE)
    return clamp_int(table.resistance_base + distance * table.distance_pct / PERCENT + atrocity * table.atrocity_pct / PERCENT - PERCENT // 4, 0, PERCENT)


async def occupy(ctx: TickContext, war: WarRow, march: March, defender: EntityRow, atlas: RegionAtlas) -> OccupationRow | None:
    region = march.profile.region_entity_id
    if region is None or not march.attacking or region == atlas.top_region(march.owner.id):
        return None
    if defender.id not in atlas.communities_in(region) and atlas.top_region(defender.id) != region:
        return None
    table = ctx.rules.occupation
    row = await ctx.session.get(OccupationRow, region)
    if row is None:
        row = OccupationRow(region_entity_id=region, occupier_entity_id=march.owner.id, war_id=war.id, since_epoch=ctx.epoch, control=0, resistance=0)
        ctx.session.add(row)
    elif row.occupier_entity_id != march.owner.id:
        row.occupier_entity_id, row.war_id, row.since_epoch, row.control = march.owner.id, war.id, ctx.epoch, 0
    row.control = clamp_int(row.control + table.control_gain, 0, PERCENT)
    row.resistance = await resistance(ctx, march.owner, defender.id)
    await advance(ctx, war.id, march.owner.id, ctx.rules.war_aims.occupation_score, target=region, kinds=REGION_AIMS)
    return row


async def partisans(ctx: TickContext) -> int:
    table = ctx.rules.occupation
    lost = 0
    for row in list(await ctx.session.scalars(select(OccupationRow).order_by(OccupationRow.region_entity_id))):
        if not ctx.rng(f"partisans.{row.region_entity_id}.{ctx.epoch}").chance(table.partisan_chance * row.resistance / PERCENT):
            continue
        armies = await ctx.session.scalars(
            select(ArmyProfileRow)
            .join(ArmyRow, ArmyRow.entity_id == ArmyProfileRow.army_entity_id)
            .where(ArmyProfileRow.region_entity_id == row.region_entity_id, ArmyRow.owner_entity_id == row.occupier_entity_id)
            .where(ArmyRow.disbanded_epoch.is_(None))
        )
        for profile in list(armies):
            army = await living_entity(ctx.session, profile.army_entity_id)
            if army is None:
                continue
            stacks = await stacks_of(ctx.session, army.id)
            lost += take(stacks, round_half_up((stat(army, "size") or 0) * table.partisan_losses_pct / PERCENT))
            sync(army, stacks, ctx.rules)
        row.control = clamp_int(row.control - table.control_gain // 2, 0, PERCENT)
    return lost


async def end_occupations(ctx: TickContext) -> int:
    ended = 0
    for row in list(await ctx.session.scalars(select(OccupationRow))):
        if held(row.region_entity_id, row.occupier_entity_id):
            continue
        war = await ctx.session.get(WarRow, row.war_id) if row.war_id is not None else None
        if war is None or war.status not in {WarStatus.ONGOING, WarStatus.MOBILIZING}:
            await ctx.session.delete(row)
            ended += 1
    return ended


def occupation_tax(ctx: TickContext, income: int, row: OccupationRow | None) -> int:
    if row is None or income <= 0:
        return 0
    return round_half_up(income * ctx.rules.occupation.tax_pct / PERCENT * row.control / PERCENT)


async def weary(ctx: TickContext, war: WarRow, side: WarSideRow, *, dead: int, maimed: int, occupied: int) -> int:
    table = ctx.rules.war_weariness
    seasons = ctx.rules.campaigns.seasons_per_war_epoch
    gain = dead * table.casualty_per_1000 / THOUSAND + maimed * table.maimed_per_100 / HUNDRED + occupied * table.occupation_gain + seasons * table.season_gain
    martial = (await values_for(ctx.session, side.entity_id)).get(ValueAxis.MARTIAL, 0)
    gain *= 1 - max(0, martial) / PERCENT * table.martial_resist_pct / PERCENT
    side.weariness = clamp_int(side.weariness + round_half_up(gain), 0, PERCENT)
    return side.weariness


async def seeks_peace(ctx: TickContext, war: WarRow, side: WarSideRow, *, humiliated: bool) -> bool:
    table = ctx.rules.war_weariness
    pressure = (side.weariness + await peace_pressure(ctx, side)) * await lean_community(ctx, side.entity_id, BiasedDecision.PEACE)
    if humiliated and (await values_for(ctx.session, side.entity_id)).get(ValueAxis.HONOUR, 0) > 0:
        pressure = round_half_up(pressure * (1 - table.honour_hold_pct / PERCENT))
    return pressure >= table.peace_threshold


async def announce_partisans(ctx: TickContext, lost: int) -> None:
    if lost:
        text = f"Partisans in occupied lands struck at the occupiers; {lost} soldiers fell."
        await ctx.chronicle(ChronicleKind.WAR, text, template_key="war.partisans", feed_category=FeedCategory.WAR)


async def occupation_over(ctx: TickContext, entity_id: int) -> OccupationRow | None:
    if await ctx.session.scalar(select(OccupationRow.region_entity_id).limit(1)) is None:
        return None
    region = (await RegionAtlas.load(ctx.session)).top_region(entity_id)
    found = await ctx.session.get(OccupationRow, region) if region is not None else None
    return found if found is not None and found.occupier_entity_id != entity_id else None


async def pay_occupier(ctx: TickContext, occupier_id: int, amount: int) -> None:
    profile = await ctx.session.scalar(
        select(ArmyProfileRow)
        .join(ArmyRow, ArmyRow.entity_id == ArmyProfileRow.army_entity_id)
        .where(ArmyRow.owner_entity_id == occupier_id, ArmyRow.disbanded_epoch.is_(None))
        .order_by(ArmyProfileRow.army_entity_id)
        .limit(1)
    )
    if profile is not None:
        profile.war_chest += amount
        return
    occupier = await living_entity(ctx.session, occupier_id)
    if occupier is not None:
        shift_stat(occupier, "wealth", amount // max(1, ctx.rules.taxation.wealth_per_treasury))
