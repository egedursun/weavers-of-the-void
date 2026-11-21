from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.creature_groups import RANKS_MAX, CreatureGroupRow
from aerona.db.tables.ecology import BeastProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.protected_nature import ProtectedAreaRow
from aerona.db.write_guard import held
from aerona.domain.enums.creature_groups import GroupAim, GroupForm
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import CreatureTrait
from aerona.engine.context import TickContext
from aerona.engine.cosmos.fauna import traits_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import record
from aerona.rules.registry import Rules

G = GroupForm
HUNTING = frozenset({G.PACK, G.HIVE, G.TROOP})
GRAZING = frozenset({G.HERD, G.FLOCK})
ROAMING = frozenset({G.HERD, G.FLOCK})
MIXED = frozenset({G.HERD, G.FLOCK})
RANKS = total(GroupForm, {G.PACK: 2, G.HERD: 1, G.COLONY: 2, G.HIVE: 3, G.TROOP: 3, G.FLOCK: 1, G.SOLITARY_RANGE: 0})
TROOP_WIT = 50
THOUSAND = 1000
RAID_SATED = 30
PRESSURE_MAX = 50


@dataclass
class GroupTally:
    formed: int = 0
    raids: int = 0
    contests: int = 0
    wars: int = 0
    moved: int = 0
    dissolved: int = 0


TRAIT_FORMS = (
    (CreatureTrait.HIVE_MIND, G.HIVE),
    (CreatureTrait.SWARM_BREEDER, G.COLONY),
    (CreatureTrait.PACK_HUNTER, G.PACK),
    (CreatureTrait.FLYING, G.FLOCK),
)


def form_for(traits: set[CreatureTrait], wit: int) -> GroupForm:
    chosen = next((form for trait, form in TRAIT_FORMS if trait in traits), None)
    if chosen is not None:
        return chosen
    if wit >= TROOP_WIT:
        return G.TROOP
    return G.SOLITARY_RANGE if CreatureTrait.AMBUSH_PREDATOR in traits else G.HERD


async def leader_of(ctx: TickContext, species_id: int, region_id: int, atlas: RegionAtlas, *, besides: int | None = None) -> int | None:
    for profile in await ctx.session.scalars(
        select(BeastProfileRow).where(BeastProfileRow.species_entity_id == species_id).order_by(BeastProfileRow.beast_entity_id)
    ):
        beast = await ctx.session.get(EntityRow, profile.beast_entity_id)
        if beast is not None and beast.status is EntityStatus.CANON and beast.id != besides and atlas.top_region(beast.id) == region_id and not held(beast.id):
            return beast.id
    return None


async def group_of(ctx: TickContext, species_id: int, region_id: int) -> CreatureGroupRow | None:
    here = (CreatureGroupRow.species_entity_id == species_id, CreatureGroupRow.region_entity_id == region_id)
    return await ctx.session.scalar(select(CreatureGroupRow).where(*here).limit(1))


async def form_groups(ctx: TickContext, atlas: RegionAtlas, tally: GroupTally) -> None:
    table = ctx.rules.creature_groups
    ranges = (
        select(SpeciesRangeRow)
        .where(SpeciesRangeRow.abundance >= table.form_floor)
        .order_by(SpeciesRangeRow.species_entity_id, SpeciesRangeRow.region_entity_id)
    )
    for row in list(await ctx.session.scalars(ranges)):
        if held(row.species_entity_id) or held(row.region_entity_id) or await group_of(ctx, row.species_entity_id, row.region_entity_id) is not None:
            continue
        species = await ctx.session.get(EntityRow, row.species_entity_id)
        if species is None:
            continue
        form = form_for(await traits_of(ctx.session, species.id), stat_or(species, "intelligence", 0))
        group = CreatureGroupRow(
            species_entity_id=species.id,
            region_entity_id=row.region_entity_id,
            form=form,
            size=row.abundance * table.size_per_abundance,
            leader_node_id=await leader_of(ctx, species.id, row.region_entity_id, atlas),
            leader_since_epoch=ctx.epoch,
            ranks=min(RANKS_MAX, RANKS[form]),
            territory=[row.region_entity_id],
            rivals=[],
            formed_epoch=ctx.epoch,
            locked=[],
        )
        ctx.session.add(group)
        await ctx.session.flush()
        await record(
            ctx,
            "beasts.group_formed",
            roles={IncidentRole.SUBJECT: species.id, IncidentRole.PLACE: row.region_entity_id},
            facts={"form": form, "size": group.size},
        )
        tally.formed += 1


async def settled_in(ctx: TickContext, atlas: RegionAtlas, region_id: int) -> int:
    total_people = 0
    for community in atlas.communities_in(region_id):
        entity = await ctx.session.get(EntityRow, community)
        if entity is not None and entity.entity_type is EntityType.SETTLEMENT:
            total_people += stat_or(entity, "population", 0)
    return total_people


async def shielded(ctx: TickContext, region_id: int) -> bool:
    live = (ProtectedAreaRow.region_entity_id == region_id, ProtectedAreaRow.lifted_epoch.is_(None))
    return await ctx.session.scalar(select(ProtectedAreaRow.id).where(*live).limit(1)) is not None


def aiming(ctx: TickContext, group: CreatureGroupRow, aim: GroupAim) -> bool:
    return group.aim is aim and group.aim_until_epoch >= ctx.epoch


async def raid(ctx: TickContext, atlas: RegionAtlas, group: CreatureGroupRow, tally: GroupTally) -> None:
    table = ctx.rules.creature_groups
    if group.form not in HUNTING or aiming(ctx, group, GroupAim.GUARD) or group.hunger < table.raid_hunger_threshold:
        return
    towns = []
    for community in atlas.communities_in(group.region_entity_id):
        town = await ctx.session.get(EntityRow, community)
        if town is not None and town.entity_type is EntityType.SETTLEMENT and not held(town.id):
            towns.append(town)
    if not towns:
        return
    town = ctx.rng(f"group.raid.{group.id}.{ctx.epoch}").pick(towns)
    add_prosperity(ctx.rules, town, -table.raid_loss)
    if "hunger" not in group.locked:
        group.hunger = clamp_int(group.hunger - RAID_SATED, 0, PERCENT)
    roles = {IncidentRole.SUBJECT: group.species_entity_id, IncidentRole.TARGET: town.id, IncidentRole.ACTOR: group.leader_node_id}
    await record(ctx, "beasts.group_raid", roles=roles, facts={"form": group.form, "size": group.size}, place=town.id)
    tally.raids += 1


async def contest(ctx: TickContext, atlas: RegionAtlas, group: CreatureGroupRow, tally: GroupTally) -> None:
    if group.form is G.SOLITARY_RANGE or "leader_node_id" in group.locked:
        return
    if not ctx.rng(f"group.contest.{group.id}.{ctx.epoch}").chance(ctx.rules.creature_groups.contest_chance_pct):
        return
    fallen = group.leader_node_id
    group.leader_node_id = await leader_of(ctx, group.species_entity_id, group.region_entity_id, atlas, besides=fallen)
    group.leader_since_epoch = ctx.epoch
    roles = {IncidentRole.SUBJECT: group.species_entity_id, IncidentRole.PREDECESSOR: fallen, IncidentRole.SUCCESSOR: group.leader_node_id}
    await record(ctx, "beasts.leader_fell", roles=roles, facts={"form": group.form}, place=group.region_entity_id)
    tally.contests += 1


async def fight(ctx: TickContext, group: CreatureGroupRow, groups: list[CreatureGroupRow], tally: GroupTally) -> None:
    if group.form not in HUNTING:
        return
    rivals = [other for other in groups if other.id != group.id and other.form in HUNTING and other.region_entity_id == group.region_entity_id]
    group.rivals = sorted(other.id for other in rivals)
    for other in rivals:
        if other.id < group.id or held(other.species_entity_id):
            continue
        if not ctx.rng(f"group.war.{group.id}.{other.id}.{ctx.epoch}").chance(ctx.rules.creature_groups.territory_war_pct):
            continue
        winner, loser = (group, other) if group.size >= other.size else (other, group)
        if "size" not in loser.locked:
            loser.size = round(loser.size * (PERCENT - ctx.rules.creature_groups.war_loss_pct) / PERCENT)
        roles = {IncidentRole.ACTOR: winner.species_entity_id, IncidentRole.TARGET: loser.species_entity_id, IncidentRole.PLACE: group.region_entity_id}
        await record(ctx, "beasts.territory_war", roles=roles, facts={"winner": winner.size, "loser": loser.size})
        tally.wars += 1


async def move_group(ctx: TickContext, atlas: RegionAtlas, group: CreatureGroupRow, to_region: int) -> None:
    source = await ctx.session.get(SpeciesRangeRow, (group.species_entity_id, group.region_entity_id))
    target = await ctx.session.get(SpeciesRangeRow, (group.species_entity_id, to_region))
    if target is None:
        target = SpeciesRangeRow(species_entity_id=group.species_entity_id, region_entity_id=to_region, abundance=0, fit=50, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(target)
    if source is not None:
        share = source.abundance // 2
        source.abundance -= share
        target.abundance = clamp_int(target.abundance + share, 0, PERCENT)
    origin = group.region_entity_id
    group.region_entity_id = to_region
    group.territory = sorted({*group.territory, to_region})
    roles = {IncidentRole.SUBJECT: group.species_entity_id, IncidentRole.ORIGIN: origin, IncidentRole.DESTINATION: to_region}
    await record(ctx, "beasts.group_moved", roles=roles, facts={"form": group.form, "size": group.size})


async def roam(ctx: TickContext, atlas: RegionAtlas, group: CreatureGroupRow, tally: GroupTally) -> None:
    table = ctx.rules.creature_groups
    if "region_entity_id" in group.locked or await shielded(ctx, group.region_entity_id):
        return
    pushed = await settled_in(ctx, atlas, group.region_entity_id) >= table.push_population
    withdraw = aiming(ctx, group, GroupAim.WITHDRAW)
    chance = table.move_pct * (2 if group.form in ROAMING else 1)
    if not (withdraw or (pushed and ctx.rng(f"group.move.{group.id}.{ctx.epoch}").chance(chance))):
        return
    options = [region for region in atlas.neighbours(group.region_entity_id) if not atlas.is_water(region) and not held(region)]
    if not options:
        return
    crowd = {region: await settled_in(ctx, atlas, region) for region in options}
    await move_group(ctx, atlas, group, min(options, key=lambda region: (crowd[region], region)))
    tally.moved += 1


async def follow_range(ctx: TickContext, atlas: RegionAtlas, group: CreatureGroupRow, tally: GroupTally) -> bool:
    table = ctx.rules.creature_groups
    row = await ctx.session.get(SpeciesRangeRow, (group.species_entity_id, group.region_entity_id))
    if row is None or row.abundance <= 0:
        if "size" not in group.locked:
            await ctx.session.delete(group)
            tally.dissolved += 1
            return False
        return True
    if "size" not in group.locked:
        grown = PERCENT + (PERCENT // 5 if aiming(ctx, group, GroupAim.GROW) else 0)
        group.size = row.abundance * table.size_per_abundance * grown // PERCENT
    if "hunger" not in group.locked:
        pressure = min(PRESSURE_MAX, await settled_in(ctx, atlas, group.region_entity_id) * PRESSURE_MAX // max(1, table.push_population))
        group.hunger = PERCENT if aiming(ctx, group, GroupAim.RAID) else clamp_int(PERCENT - row.fit + pressure, 0, PERCENT)
    return True


async def tend_groups(ctx: TickContext) -> GroupTally:
    tally = GroupTally()
    atlas = await RegionAtlas.load(ctx.session)
    await form_groups(ctx, atlas, tally)
    alive = []
    for group in list(await ctx.session.scalars(select(CreatureGroupRow).order_by(CreatureGroupRow.id))):
        if not held(group.species_entity_id) and not held(group.region_entity_id) and await follow_range(ctx, atlas, group, tally):
            alive.append(group)
    for group in alive:
        await raid(ctx, atlas, group, tally)
        await contest(ctx, atlas, group, tally)
        await fight(ctx, group, alive, tally)
        await roam(ctx, atlas, group, tally)
    return tally


async def group_danger(session: AsyncSession, rules: Rules) -> dict[int, float]:
    found: dict[int, float] = {}
    for group in await session.scalars(select(CreatureGroupRow).where(CreatureGroupRow.form.in_(sorted(HUNTING))).order_by(CreatureGroupRow.id)):
        found[group.region_entity_id] = found.get(group.region_entity_id, 0.0) + group.size / THOUSAND * rules.creature_groups.travel_danger_pct
    return found


async def hunt_factor(session: AsyncSession, rules: Rules, species_id: int, region_id: int) -> float:
    here = (CreatureGroupRow.species_entity_id == species_id, CreatureGroupRow.region_entity_id == region_id, CreatureGroupRow.form.in_(sorted(GRAZING)))
    group = await session.scalar(select(CreatureGroupRow).where(*here).limit(1))
    return 1 + group.size / THOUSAND * rules.creature_groups.hunt_bonus_pct / PERCENT if group is not None else 1.0
