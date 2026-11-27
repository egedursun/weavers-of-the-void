from sqlalchemy import func, select
from sqlalchemy.orm import aliased

from aerona.catalog.beast_tempers import GATHERING, GUARDING, REMEMBERING
from aerona.catalog.terrain import TERRAIN
from aerona.constants.units import PERCENT
from aerona.db.fixups import fixup_due
from aerona.db.tables.anatomy import CreatureAnatomyRow
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.ecology import BeastGrudgeRow, BeastProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import LeyLineRow, RegionEnvironmentRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.polity import HouseMemberRow
from aerona.db.write_guard import held
from aerona.domain.enums.ecology import Habitat
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import TemperatureBand, TerrainKind, TerrainTrait
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.ecology.beast_acts import HOARD_ROBBED
from aerona.engine.economy.purse import coin_of
from aerona.engine.economy.stocks import goods_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import towns_of_people
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat, stat_or
from aerona.engine.recording.record import record

BeastRobbedRole = aliased(IncidentParticipantRow)


async def grudge_holder_of(ctx: TickContext, wounder_id: int) -> int:
    house = await ctx.session.scalar(
        select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == wounder_id).order_by(HouseMemberRow.house_entity_id).limit(1)
    )
    return house if house is not None else wounder_id


async def keep_grudges(ctx: TickContext, beast: EntityRow, anatomy: CreatureAnatomyRow | None) -> list[BeastGrudgeRow]:
    table = ctx.rules.beast_acts
    grudges = list(await ctx.session.scalars(select(BeastGrudgeRow).where(BeastGrudgeRow.beast_entity_id == beast.id).order_by(BeastGrudgeRow.id)))
    if anatomy is None or anatomy.temperament not in REMEMBERING or held(beast.id):
        return grudges
    held_against = {row.target_node_id for row in grudges}
    harms = await ctx.session.scalars(
        select(MemoryRow).where(MemoryRow.holder_node_id == beast.id, MemoryRow.kind == MemoryKind.HARMED_ME).order_by(MemoryRow.id)
    )
    fresh: set[int] = set()
    for memory in list(harms):
        if memory.subject_node_id is None:
            continue
        target = await grudge_holder_of(ctx, memory.subject_node_id)
        fresh.add(target)
        if target in held_against:
            continue
        row = BeastGrudgeRow(beast_entity_id=beast.id, target_node_id=target, strength=PERCENT // 2, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
        grudges.append(row)
        held_against.add(target)
        await record(ctx, "beast.grudge_sworn", roles={IncidentRole.SUBJECT: beast.id, IncidentRole.TARGET: target}, facts={"strength": row.strength})
    for row in grudges:
        if row.target_node_id not in fresh and "strength" not in row.locked:
            row.strength = clamp_int(row.strength - table.grudge_fade, 0, PERCENT)
    for row in [row for row in grudges if row.strength <= 0 and "strength" not in row.locked]:
        await ctx.session.delete(row)
        grudges.remove(row)
    return grudges


async def homes_of_target(ctx: TickContext, target_id: int) -> set[int]:
    node = await ctx.session.get(EntityRow, target_id)
    if node is None:
        return set()
    if node.entity_type is EntityType.PEOPLE:
        return set(await towns_of_people(ctx.session, node.id))
    members = select(HouseMemberRow.mortal_entity_id).where(HouseMemberRow.house_entity_id == node.id)
    homes = set(await ctx.session.scalars(select(EntityRow.location_id).where(EntityRow.id.in_(members), EntityRow.location_id.is_not(None))))
    if node.location_id is not None:
        homes.add(node.location_id)
    return {home for home in homes if home is not None}


async def grudge_town(ctx: TickContext, atlas: RegionAtlas, row: BeastProfileRow, grudges: list[BeastGrudgeRow]) -> tuple[EntityRow, BeastGrudgeRow] | None:
    lair = row.lair_place_id
    if lair is None:
        return None
    reach = ctx.rules.beast_acts.vengeance_reach
    for grudge in sorted(grudges, key=lambda item: (-item.strength, item.id)):
        for home in sorted(await homes_of_target(ctx, grudge.target_node_id)):
            town = await ctx.session.get(EntityRow, home)
            if town is not None and town.status is EntityStatus.CANON and town.entity_type is EntityType.SETTLEMENT and atlas.distance(lair, town.id) <= reach:
                return town, grudge
    return None


async def richest(ctx: TickContext, near: list[EntityRow]) -> EntityRow | None:
    best: tuple[int, int, EntityRow] | None = None
    for town in near:
        worth = await coin_of(ctx.session, ctx.rules, town)
        if best is None or (worth, -town.id) > (best[0], -best[1]):
            best = (worth, town.id, town)
    return best[2] if best is not None else None


def gathers(anatomy: CreatureAnatomyRow | None) -> bool:
    return anatomy is not None and anatomy.temperament in GATHERING


async def guard_land(ctx: TickContext, atlas: RegionAtlas, beast: EntityRow, row: BeastProfileRow, anatomy: CreatureAnatomyRow | None) -> int:
    if anatomy is None or anatomy.temperament not in GUARDING or row.lair_place_id is None:
        return 0
    region = atlas.top_region(row.lair_place_id)
    share = ctx.rules.beast_acts.protective_strike_pct
    struck = 0
    armies = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.ARMY, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for army in list(armies):
        if held(army.id) or region is None or atlas.top_region(army.id) != region or army.id == row.bound_to_node_id:
            continue
        lost = round_half_up(stat_or(army, "size", 0) * share / PERCENT)
        if lost <= 0:
            continue
        shift_stat(army, "size", -lost, 0)
        struck += 1
        await record(
            ctx,
            "beast.guarded",
            roles={IncidentRole.SUBJECT: beast.id, IncidentRole.TARGET: army.id, IncidentRole.PLACE: region},
            facts={"lost": lost},
            place=region,
        )
    return struck


async def habitat_ways(ctx: TickContext, beast: EntityRow, row: BeastProfileRow, anatomy: CreatureAnatomyRow | None, region: int | None) -> bool:
    if anatomy is None or region is None or held(beast.id):
        return False
    table = ctx.rules.habitats
    ground = await ctx.session.get(RegionEnvironmentRow, region)
    if anatomy.habitat is Habitat.MAGMA:
        if ground is not None and ground.temperature_band is TemperatureBand.FROZEN and TerrainTrait.WATERY in TERRAIN[ground.dominant_terrain].traits:
            shift_stat(beast, "hp", -max(1, row.endurance // 4), 0)
        if row.bound_to_node_id is not None:
            await goods_of(ctx.session, ctx.epoch).add(row.bound_to_node_id, CommodityKind.FUEL, max(1, row.endurance // 10), GoodsFlow.HARVEST)
        volcanic = ground is not None and ground.dominant_terrain is TerrainKind.VOLCANIC
        if volcanic and ctx.rng(f"beast.surface.{beast.id}.{ctx.epoch}").chance(table.magma_surface_pct):
            await record(ctx, "beast.surfaced", roles={IncidentRole.SUBJECT: beast.id, IncidentRole.PLACE: region}, place=region)
            return True
    if anatomy.habitat is Habitat.ETHEREAL:
        lines = await ctx.session.scalar(select(func.count(LeyLineRow.id)).where((LeyLineRow.region_a_id == region) | (LeyLineRow.region_b_id == region)))
        chance = table.ethereal_cross_pct * (2 if lines else 1)
        if ctx.rng(f"beast.cross.{beast.id}.{ctx.epoch}").chance(chance):
            await record(ctx, "beast.crossed_over", roles={IncidentRole.SUBJECT: beast.id, IncidentRole.PLACE: region}, place=region)
            return True
    return False


GRUDGES_FIXUP = "beast_acts.w52_grudges"


async def wrongs_against(ctx: TickContext, beast_id: int) -> list[tuple[int, int | None]]:
    wounds = await ctx.session.execute(
        select(InjuryRow.cause_node_id, InjuryRow.incident_id)
        .where(InjuryRow.bearer_node_id == beast_id, InjuryRow.cause_node_id.is_not(None))
        .order_by(InjuryRow.id)
    )
    robbed = await ctx.session.execute(
        select(IncidentParticipantRow.node_id, IncidentRow.id)
        .join(IncidentRow, IncidentRow.id == IncidentParticipantRow.incident_id)
        .join(BeastRobbedRole, BeastRobbedRole.incident_id == IncidentRow.id)
        .where(IncidentRow.kind == HOARD_ROBBED, IncidentParticipantRow.role == IncidentRole.ACTOR, BeastRobbedRole.node_id == beast_id)
        .order_by(IncidentRow.id)
    )
    return [(node, incident) for node, incident in [*wounds, *robbed] if node is not None]


async def backfill_grudges(ctx: TickContext) -> int:
    if not await fixup_due(ctx.session, GRUDGES_FIXUP):
        return 0
    sworn = 0
    for anatomy in list(
        await ctx.session.scalars(
            select(CreatureAnatomyRow).where(CreatureAnatomyRow.temperament.in_(sorted(REMEMBERING))).order_by(CreatureAnatomyRow.node_id)
        )
    ):
        if held(anatomy.node_id):
            continue
        held_against = set(await ctx.session.scalars(select(BeastGrudgeRow.target_node_id).where(BeastGrudgeRow.beast_entity_id == anatomy.node_id)))
        for wronger, incident in await wrongs_against(ctx, anatomy.node_id):
            target = await grudge_holder_of(ctx, wronger)
            if target in held_against or target == anatomy.node_id:
                continue
            ctx.session.add(
                BeastGrudgeRow(
                    beast_entity_id=anatomy.node_id, target_node_id=target, cause_incident_id=incident, strength=PERCENT // 2, since_epoch=ctx.epoch, locked=[]
                )
            )
            held_against.add(target)
            sworn += 1
    ctx.session.add(AppliedFixupRow(key=GRUDGES_FIXUP, result={"grudges": sworn}))
    await ctx.session.flush()
    return sworn
