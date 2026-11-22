from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.agrarian import GameReserveRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.gardens import GardenRow
from aerona.db.tables.protected_nature import ProtectedAreaRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.garden import GardenKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.protected_nature import ProtectedUse, ProtectionBasis
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.mirrors import close_legacy, first_sight
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.protected_nature.book import LIVELIHOODS, NatureTally, effective, open_areas, uses_of
from aerona.engine.recording.record import record

LEGACY_FIXUP = "protected_areas.legacy"
RESERVE_FAMILY = "protected_areas.reserve"
GROVE_FAMILY = "protected_areas.grove"
PB = ProtectionBasis
BASIS_STRENGTH = total(ProtectionBasis, {PB.LAW: 60, PB.FAITH: 50, PB.CUSTOM: 40, PB.CHARTER: 50, PB.DIVINE_DECREE: 70})
HALF = PERCENT // 2
TENTHS = 10


async def protect_area(
    ctx: TickContext,
    region: EntityRow,
    basis: ProtectionBasis,
    uses: list[ProtectedUse],
    tally: NatureTally,
    *,
    protector: int | None = None,
    site: int | None = None,
) -> ProtectedAreaRow:
    found = next((row for row in await open_areas(ctx.session) if row.region_entity_id == region.id and row.site_entity_id == site), None)
    row = found or ProtectedAreaRow(region_entity_id=region.id, site_entity_id=site, since_epoch=ctx.epoch, locked=[])
    if "banned_uses" not in (row.locked or []):
        row.banned_uses = sorted({*(row.banned_uses or []), *(use.value for use in uses)})
    row.protector_node_id, row.basis = protector if protector is not None else row.protector_node_id, basis
    if found is None:
        row.strength = BASIS_STRENGTH[basis]
        ctx.session.add(row)
    await ctx.session.flush()
    tally.areas += 1
    await record(
        ctx,
        "nature.area_protected",
        roles={IncidentRole.SUBJECT: region.id, IncidentRole.ACTOR: row.protector_node_id},
        facts={"basis": basis, "uses": ", ".join(use.value.replace("_", " ") for use in uses) or "nothing"},
    )
    return row


async def lift(ctx: TickContext, row: ProtectedAreaRow, tally: NatureTally) -> None:
    row.lifted_epoch = ctx.epoch
    tally.lifted += 1
    await record(ctx, "nature.protection_lifted", roles={IncidentRole.SUBJECT: row.region_entity_id}, facts={"basis": row.basis})


async def towns_around(ctx: TickContext, atlas: RegionAtlas, region: int) -> list[EntityRow]:
    towns = [await living_entity(ctx.session, node) for node in atlas.communities_in(region)]
    return [town for town in towns if town is not None and town.entity_type is EntityType.SETTLEMENT and not held(town.id)]


async def recover(ctx: TickContext, row: ProtectedAreaRow, strength: int) -> None:
    gain = ctx.rules.protected_nature.recovery_per_epoch * strength // PERCENT
    uses = uses_of(row)
    land = await ctx.session.get(RegionEnvironmentRow, row.region_entity_id)
    if land is not None and gain:
        if ProtectedUse.LOGGING in uses and "forest_cover" not in (land.locked or []):
            land.forest_cover = clamp_int(min(land.base_forest, land.forest_cover + gain), 0, PERCENT)
        if ProtectedUse.FARMING in uses and "farmed" not in (land.locked or []):
            land.farmed = clamp_int(land.farmed - gain, 0, PERCENT)
        if uses & {ProtectedUse.SETTLEMENT, ProtectedUse.BUILDING} and "cleared" not in (land.locked or []):
            land.cleared = clamp_int(land.cleared - gain, 0, PERCENT)
    if not uses & {ProtectedUse.HUNTING, ProtectedUse.FISHING, ProtectedUse.ENTRY}:
        return
    for wild in await ctx.session.scalars(
        select(SpeciesRangeRow).where(SpeciesRangeRow.region_entity_id == row.region_entity_id).order_by(SpeciesRangeRow.species_entity_id)
    ):
        if wild.abundance > 0 and "abundance" not in (wild.locked or []):
            wild.abundance = clamp_int(wild.abundance + max(1, wild.abundance * gain // PERCENT), 0, PERCENT)


async def poach(ctx: TickContext, row: ProtectedAreaRow, strength: int, towns: list[EntityRow], tally: NatureTally) -> None:
    table = ctx.rules.protected_nature
    land = await ctx.session.get(RegionEnvironmentRow, row.region_entity_id)
    hunger = max(0, PERCENT - land.harvest_pct) if land is not None else 0
    wealth = sum((stat(town, "prosperity") or 0) for town in towns) // len(towns) if towns else HALF
    want = hunger + max(0, HALF - wealth)
    aim = clamp_int(round_half_up((PERCENT - strength) * want * table.poaching_per_price_pct / (PERCENT * TENTHS)), 0, PERCENT)
    if "poaching" in (row.locked or []):
        return
    before = row.poaching
    row.poaching = clamp_int(before + (aim - before) // 2, 0, PERCENT)
    if row.poaching >= table.poached_at > before:
        tally.poached += 1
        await record(ctx, "nature.poached", roles={IncidentRole.SUBJECT: row.region_entity_id}, facts={"poaching": row.poaching})


async def displace(ctx: TickContext, row: ProtectedAreaRow, strength: int, towns: list[EntityRow]) -> None:
    table = ctx.rules.protected_nature
    banned = len(uses_of(row) & LIVELIHOODS)
    if not banned:
        return
    for town in towns:
        shift_stat(town, "prosperity", -(table.livelihood_prosperity * banned * strength // PERCENT))
        profile = await ctx.session.get(SettlementProfileRow, town.id)
        if profile is not None and "unrest" not in (profile.locked or []):
            profile.unrest = clamp_int(profile.unrest + table.displacement_grievance * strength // PERCENT, 0, PERCENT)


async def tend_areas(ctx: TickContext, tally: NatureTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    for row in await open_areas(ctx.session):
        if held(row.region_entity_id):
            continue
        protector = await living_entity(ctx.session, row.protector_node_id) if row.protector_node_id is not None else None
        if row.protector_node_id is not None and protector is None:
            await lift(ctx, row, tally)
            continue
        strength = effective(ctx.rules, row) * (PERCENT - row.poaching) // PERCENT
        towns = await towns_around(ctx, atlas, row.region_entity_id)
        await recover(ctx, row, strength)
        await poach(ctx, row, strength, towns, tally)
        await displace(ctx, row, strength, towns)


async def protect_rights(ctx: TickContext, tally: NatureTally) -> None:
    before = tally.areas
    ever = {(row.region_entity_id, row.site_entity_id) for row in await ctx.session.scalars(select(ProtectedAreaRow).order_by(ProtectedAreaRow.id))}
    for reserve in list(await ctx.session.scalars(select(GameReserveRow).order_by(GameReserveRow.id))):
        region = await living_entity(ctx.session, reserve.region_entity_id)
        if region is None or held(region.id) or not await first_sight(ctx.session, RESERVE_FAMILY, reserve.id) or (region.id, None) in ever:
            continue
        area = await protect_area(ctx, region, ProtectionBasis.LAW, [ProtectedUse.HUNTING], tally, protector=reserve.holder_node_id)
        area.strength = reserve.strictness
        ever.add((region.id, None))
    atlas = await RegionAtlas.load(ctx.session)
    for grove in list(await ctx.session.scalars(select(GardenRow).where(GardenRow.kind == GardenKind.SACRED_GROVE).order_by(GardenRow.id))):
        region_id = atlas.top_region(grove.settlement_entity_id)
        region = await living_entity(ctx.session, region_id) if region_id is not None else None
        if region is None or held(region.id) or not await first_sight(ctx.session, GROVE_FAMILY, grove.id):
            continue
        if (region.id, grove.structure_entity_id) not in ever:
            await protect_area(ctx, region, ProtectionBasis.FAITH, [ProtectedUse.LOGGING], tally, site=grove.structure_entity_id)
            ever.add((region.id, grove.structure_entity_id))
    await close_legacy(ctx.session, LEGACY_FIXUP, {"areas": tally.areas - before})
    await ctx.session.flush()
