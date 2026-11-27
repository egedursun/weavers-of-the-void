from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.fixups import fixup_due
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.mass_weapons import WarRemnantRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.warfare import BattleRow, WarRow, WarSideRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import ScarKind
from aerona.domain.enums.mass_weapons import RemnantKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import take_coin
from aerona.engine.environment.book import add_scar
from aerona.engine.industry.sky import irradiate
from aerona.engine.lifecycle.wounds import slay
from aerona.engine.lore.research import techniques_of
from aerona.engine.mass_weapons.book import ArsenalTally
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.recording.record import record

LEGACY_FIXUP = "war_remnants.legacy"
REMNANT_DEATH = "was killed by what a war left in the land"
TENTHS = 1000
PROSPERITY_SHARE = 20
CANDIDATES = 40
LAND_ARMS = ((Technique.GUNPOWDER, RemnantKind.BURIED_CHARGES), (Technique.NECROMANCY, RemnantKind.UNQUIET_DEAD))


POISONING = frozenset({RemnantKind.POISONED_GROUND, RemnantKind.FALLOUT})


async def leave_remnant(
    ctx: TickContext,
    kind: RemnantKind,
    density: int,
    tally: ArsenalTally,
    *,
    region: int | None = None,
    orbit: int | None = None,
    war: int | None = None,
    weapon: int | None = None,
) -> WarRemnantRow | None:
    if (region is None) == (orbit is None) or (region is not None and held(region)):
        return None
    ground = await ctx.session.get(RegionEnvironmentRow, region) if region is not None and kind in POISONING else None
    if ground is not None:
        add_scar(ground, ScarKind.POISONED, density)
    if region is not None and kind is RemnantKind.FALLOUT:
        await irradiate(ctx.session, region, density, ctx.epoch)
    query = select(WarRemnantRow).where(WarRemnantRow.kind == kind, WarRemnantRow.region_entity_id == region, WarRemnantRow.orbit_world_id == orbit)
    found = await ctx.session.scalar(query.order_by(WarRemnantRow.id).limit(1))
    if found is not None:
        if "density" not in (found.locked or []):
            found.density = clamp_int(max(found.density, density), 0, PERCENT)
        return found
    row = WarRemnantRow(
        region_entity_id=region,
        orbit_world_id=orbit,
        kind=kind,
        density=clamp_int(density, 0, PERCENT),
        decay_per_epoch=ctx.rules.mass_weapons.remnant_decay_per_epoch,
        war_id=war,
        weapon_id=weapon,
        created_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    tally.remnants += 1
    return row


async def towns_in(ctx: TickContext, atlas: RegionAtlas, region: int) -> list[EntityRow]:
    towns = [await living_entity(ctx.session, node) for node in atlas.communities_in(region)]
    return [town for town in towns if town is not None and town.entity_type is EntityType.SETTLEMENT and not held(town.id)]


async def harm_residents(ctx: TickContext, atlas: RegionAtlas, row: WarRemnantRow, tally: ArsenalTally) -> None:
    if row.region_entity_id is None:
        return
    table = ctx.rules.mass_weapons
    towns = await towns_in(ctx, atlas, row.region_entity_id)
    dead = 0
    for town in towns:
        lost = round_half_up((stat(town, "population") or 0) * table.remnant_harm_per_density * row.density / (TENTHS * PERCENT))
        shift_stat(town, "population", -lost)
        shift_stat(town, "prosperity", -(row.density // PROSPERITY_SHARE))
        dead += lost
    if towns and ctx.rng(f"remnant.kills.{row.id}.{ctx.epoch}").chance(table.resident_harm_chance_pct * row.density / PERCENT):
        here = await present_among(ctx.session, [town.id for town in towns])
        query = select(EntityRow.id).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, here)
        pool = [node for node in await ctx.session.scalars(query.order_by(EntityRow.id).limit(CANDIDATES)) if not held(node)]
        chosen = ctx.rng(f"remnant.victim.{row.id}.{ctx.epoch}").pick_or_none(pool)
        victim = await living_entity(ctx.session, chosen) if chosen is not None else None
        if victim is not None and await slay(ctx, victim, Harm(ctx.rules.casualties.wound_hp, HarmCause.ACCIDENT, REMNANT_DEATH)):
            dead += 1
    if dead:
        tally.remnant_dead += dead
        await record(
            ctx, "war.remnant_harm", roles={IncidentRole.SUBJECT: row.region_entity_id}, facts={"kind": row.kind, "dead": dead, "density": row.density}
        )


async def clear(ctx: TickContext, payer: EntityRow, region: int, budget: int, tally: ArsenalTally) -> int:
    if not await take_coin(ctx.session, ctx.rules, payer, budget):
        return 0
    cut = ctx.rules.mass_weapons.clearance_per_budget * budget // PERCENT
    cleared = 0
    for row in list(await ctx.session.scalars(select(WarRemnantRow).where(WarRemnantRow.region_entity_id == region).order_by(WarRemnantRow.id))):
        if "density" in (row.locked or []):
            continue
        taken = min(row.density, cut)
        row.density -= taken
        row.cleared = clamp_int(row.cleared + taken, 0, PERCENT)
        cleared += taken
    if cleared:
        tally.cleared += cleared
        await record(
            ctx, "war.remnants_cleared", roles={IncidentRole.ACTOR: payer.id, IncidentRole.SUBJECT: region}, facts={"cleared": cleared, "spent": budget}
        )
    return cleared


async def owner_of(ctx: TickContext, atlas: RegionAtlas, region: int) -> EntityRow | None:
    towns = [node for node in atlas.communities_in(region)]
    if not towns:
        return None
    query = select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id.in_(towns)).order_by(PolityMemberRow.polity_entity_id)
    realm = await ctx.session.scalar(query.limit(1))
    return await living_entity(ctx.session, realm) if realm is not None else None


async def tend_remnants(ctx: TickContext, tally: ArsenalTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    table = ctx.rules.mass_weapons
    for row in list(await ctx.session.scalars(select(WarRemnantRow).order_by(WarRemnantRow.id))):
        if row.region_entity_id is not None and held(row.region_entity_id):
            continue
        await harm_residents(ctx, atlas, row, tally)
        if "density" not in (row.locked or []):
            row.density = clamp_int(row.density - row.decay_per_epoch, 0, PERCENT)
        if row.region_entity_id is not None and row.density:
            owner = await owner_of(ctx, atlas, row.region_entity_id)
            if owner is not None and not held(owner.id) and ctx.rng(f"remnant.clear.{row.id}.{ctx.epoch}").chance(table.clearance_chance_pct):
                await clear(ctx, owner, row.region_entity_id, table.clearance_spend, tally)
        if not row.density and "density" not in (row.locked or []):
            await ctx.session.delete(row)


async def left_by(ctx: TickContext, atlas: RegionAtlas, war: WarRow, tally: ArsenalTally) -> None:
    sides = list(await ctx.session.scalars(select(WarSideRow.entity_id).where(WarSideRow.war_id == war.id).order_by(WarSideRow.entity_id)))
    known: set[Technique] = set()
    for side in sides:
        known |= await techniques_of(ctx.session, side)
    elapsed = max(0, ctx.epoch - (war.ended_epoch if war.ended_epoch is not None else ctx.epoch))
    density = ctx.rules.mass_weapons.remnant_density // 2 - elapsed * ctx.rules.mass_weapons.remnant_decay_per_epoch
    if density <= 0:
        return
    places = sorted({place for place in await ctx.session.scalars(select(BattleRow.place_entity_id).where(BattleRow.war_id == war.id)) if place is not None})
    regions = sorted({region for region in (atlas.top_region(place) for place in places) if region is not None})
    for technique, kind in LAND_ARMS:
        if technique in known:
            for region in regions:
                await leave_remnant(ctx, kind, density, tally, region=region, war=war.id)
    if Technique.ROCKETRY in known and regions:
        await leave_remnant(ctx, RemnantKind.WRECK_FIELD, density, tally, orbit=war.world_id, war=war.id)


async def after_wars(ctx: TickContext, tally: ArsenalTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    legacy = await fixup_due(ctx.session, LEGACY_FIXUP)
    query = select(WarRow).where(WarRow.ended_epoch.is_not(None)) if legacy else select(WarRow).where(WarRow.ended_epoch == ctx.epoch)
    for war in list(await ctx.session.scalars(query.order_by(WarRow.id))):
        await left_by(ctx, atlas, war, tally)
    if legacy:
        ctx.session.add(AppliedFixupRow(key=LEGACY_FIXUP, result={"remnants": tally.remnants}))
        await ctx.session.flush()
