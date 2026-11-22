from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.catch import GROUNDS
from aerona.constants.units import PERCENT
from aerona.db.tables.crafts import CatchGroundRow
from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.economy import ResourceProfileRow, ResourceWorkerRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import BodyPlan, HarmCause
from aerona.domain.enums.crafts import CatchGround, CatchRight
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.war import WarCause
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.crafts.catch import LAND_GROUNDS
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.naming import seed_of
from aerona.engine.recording.record import record
from aerona.engine.services.community_relations import change_relation, relation
from aerona.engine.services.war import declare_war


@dataclass
class GroundTally:
    read: int = 0
    collapsed: int = 0
    recovered: int = 0
    hurt: int = 0
    poached: int = 0
    wars: int = 0


async def owner_of(ctx: TickContext, community_id: int) -> int:
    realm = await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == community_id).limit(1))
    return realm if realm is not None else community_id


async def seed_fisheries(ctx: TickContext, atlas: RegionAtlas, tally: GroundTally) -> None:
    table = ctx.rules.grounds
    known = {row.source_entity_id for row in await ctx.session.scalars(select(CatchGroundRow))}
    profiles = await ctx.session.scalars(
        select(ResourceProfileRow)
        .where(ResourceProfileRow.commodity == CommodityKind.FISH, ResourceProfileRow.revealed.is_(True))
        .order_by(ResourceProfileRow.resource_entity_id)
    )
    for profile in list(profiles):
        resource = await ctx.session.get(EntityRow, profile.resource_entity_id)
        region = atlas.top_region(profile.resource_entity_id)
        if resource is None or resource.status is not EntityStatus.CANON or region is None or resource.id in known or held(resource.id):
            continue
        rng = ctx.rng(seed_of("ground", resource.id))
        ground = CatchGround.MARINE_HUNT if rng.chance(table.marine_hunt_chance) else CatchGround.FISHERY
        worker = await ctx.session.scalar(
            select(ResourceWorkerRow.community_entity_id)
            .where(ResourceWorkerRow.resource_entity_id == resource.id)
            .order_by(ResourceWorkerRow.community_entity_id)
            .limit(1)
        )
        owned = worker is not None and rng.chance(table.owned_chance)
        ctx.session.add(
            CatchGroundRow(
                source_entity_id=resource.id,
                region_entity_id=region,
                ground=ground,
                gear=rng.pick(list(GROUNDS[ground].gear)),
                right=CatchRight.OWNED if owned else CatchRight.COMMONS,
                owner_node_id=await owner_of(ctx, worker) if owned and worker is not None else None,
                first_stock=max(1, profile.initial_reserve),
                locked=[],
            )
        )
        tally.read += 1
    await ctx.session.flush()


async def seed_land(ctx: TickContext, tally: GroundTally) -> None:
    table = ctx.rules.grounds
    known = {(row.source_entity_id, row.region_entity_id) for row in await ctx.session.scalars(select(CatchGroundRow))}
    ranges = await ctx.session.scalars(
        select(SpeciesRangeRow).where(SpeciesRangeRow.hunted > 0).order_by(SpeciesRangeRow.species_entity_id, SpeciesRangeRow.region_entity_id)
    )
    for row in list(ranges):
        key = (row.species_entity_id, row.region_entity_id)
        if key in known or held(row.species_entity_id):
            continue
        profile = await ctx.session.get(SpeciesProfileRow, row.species_entity_id)
        rng = ctx.rng(seed_of("ground", *key))
        fowling = profile.body_plan is BodyPlan.AVIAN if profile is not None else rng.chance(table.fowling_chance)
        ground = CatchGround.FOWLING if fowling else CatchGround.TRAPPING
        ctx.session.add(
            CatchGroundRow(
                source_entity_id=row.species_entity_id,
                region_entity_id=row.region_entity_id,
                ground=ground,
                gear=rng.pick(list(GROUNDS[ground].gear)),
                first_stock=max(1, row.abundance),
                locked=[],
            )
        )
        tally.read += 1
    await ctx.session.flush()


def abundance_pct(row: CatchGroundRow, profile: ResourceProfileRow | None, range_row: SpeciesRangeRow | None) -> int | None:
    stock = range_row.abundance if range_row is not None else profile.reserve if profile is not None else None
    return None if stock is None else round(stock * PERCENT / max(1, row.first_stock))


async def judge(ctx: TickContext, row: CatchGroundRow, tally: GroundTally) -> None:
    profile = await ctx.session.get(ResourceProfileRow, row.source_entity_id) if row.ground not in LAND_GROUNDS else None
    range_row = await ctx.session.get(SpeciesRangeRow, (row.source_entity_id, row.region_entity_id)) if row.ground in LAND_GROUNDS else None
    left = abundance_pct(row, profile, range_row)
    if "last_catch" not in row.locked:
        row.last_catch = (profile.last_output if profile is not None else range_row.hunted if range_row is not None else 0) or 0
    if left is None or "collapsed" in row.locked:
        return
    if not row.collapsed and left < row.collapse_at:
        row.collapsed = True
        tally.collapsed += 1
        await record(
            ctx,
            "grounds.collapsed",
            roles={IncidentRole.SUBJECT: row.source_entity_id, IncidentRole.PLACE: row.region_entity_id},
            facts={"ground": row.ground, "left": left, "collapse_at": row.collapse_at, "last_catch": row.last_catch},
            place=row.region_entity_id,
        )
    elif row.collapsed and left >= ctx.rules.grounds.recover_at:
        row.collapsed = False
        tally.recovered += 1
        await record(
            ctx,
            "grounds.recovered",
            roles={IncidentRole.SUBJECT: row.source_entity_id, IncidentRole.PLACE: row.region_entity_id},
            facts={"ground": row.ground, "left": left, "recover_at": ctx.rules.grounds.recover_at},
            place=row.region_entity_id,
        )


async def workers_of(ctx: TickContext, row: CatchGroundRow) -> list[int]:
    if row.ground in LAND_GROUNDS:
        return list(
            await ctx.session.scalars(
                select(EntityRow.id)
                .where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.location_id == row.region_entity_id)
                .order_by(EntityRow.id)
            )
        )
    return list(
        await ctx.session.scalars(
            select(ResourceWorkerRow.community_entity_id)
            .where(ResourceWorkerRow.resource_entity_id == row.source_entity_id, ResourceWorkerRow.workers > 0)
            .order_by(ResourceWorkerRow.community_entity_id)
        )
    )


async def hunt_risk(ctx: TickContext, row: CatchGroundRow, workers: list[int], tally: GroundTally) -> None:
    table = ctx.rules.grounds
    if row.ground is not CatchGround.MARINE_HUNT or row.last_catch <= 0 or not workers:
        return
    rng = ctx.rng(seed_of("ground.risk", row.source_entity_id, ctx.epoch))
    if not rng.chance(table.marine_risk):
        return
    hunters = list(
        await ctx.session.scalars(
            select(EntityRow)
            .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, workers))
            .order_by(EntityRow.id)
        )
    )
    hunters = [hunter for hunter in hunters if not held(hunter.id)]
    if not hunters:
        return
    hurt = rng.pick(hunters)
    await apply_hits(ctx, hurt, Harm(damage=table.marine_harm, cause=HarmCause.ACCIDENT, death_cause="was killed on a hunt of great sea beasts"))
    tally.hurt += 1


async def poaching(ctx: TickContext, row: CatchGroundRow, workers: list[int], tally: GroundTally) -> None:
    if row.right is not CatchRight.OWNED or row.owner_node_id is None or row.collapsed:
        return
    for community in workers:
        if community == row.owner_node_id or await owner_of(ctx, community) == row.owner_node_id or held(community):
            continue
        await change_relation(ctx, row.owner_node_id, community, -ctx.rules.grounds.poach_opinion, MemoryKind.ILL_WILL, note="took from grounds that were ours")
        tally.poached += 1
        await dispute(ctx, row, community, tally)


async def dispute(ctx: TickContext, row: CatchGroundRow, community: int, tally: GroundTally) -> None:
    table = ctx.rules.grounds
    owner = row.owner_node_id
    if owner is None or held(owner) or await relation(ctx.session, ctx.rules, owner, community) > table.war_at:
        return
    if not ctx.rng(seed_of("ground.war", row.source_entity_id, community, ctx.epoch)).chance(table.war_pct):
        return
    source = await ctx.session.get(EntityRow, row.source_entity_id)
    named = source.name if source is not None else "its waters"
    if await declare_war(ctx, owner, community, f"over the working of {named}", cause=WarCause.RESOURCE):
        tally.wars += 1


async def keep_grounds(ctx: TickContext, tally: GroundTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    await seed_fisheries(ctx, atlas, tally)
    await seed_land(ctx, tally)
    for row in list(await ctx.session.scalars(select(CatchGroundRow).order_by(CatchGroundRow.source_entity_id, CatchGroundRow.region_entity_id))):
        if held(row.source_entity_id) or held(row.region_entity_id):
            continue
        await judge(ctx, row, tally)
        workers = await workers_of(ctx, row)
        await hunt_risk(ctx, row, workers, tally)
        await poaching(ctx, row, workers, tally)
    await ctx.session.flush()
