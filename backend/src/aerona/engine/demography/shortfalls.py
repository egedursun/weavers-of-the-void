from collections.abc import Mapping

from sqlalchemy import select

from aerona.catalog.needs import SHORTFALLS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.happenings import EventFootprintRow
from aerona.db.tables.settlement import SettlementInfrastructureRow, SettlementProfileRow
from aerona.db.tables.society_depth import CommunityShortfallRow
from aerona.db.tables.warfare import SiegeRow
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society_depth import ShortfallEffect
from aerona.domain.enums.war import SiegeStatus
from aerona.engine.context import TickContext
from aerona.engine.primitives.kept import kept_rows
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import stat
from aerona.engine.recording.record import record
from aerona.engine.urban.coverage import WATER_OF

HELD_SHORT = "short_pct"


async def in_drought(ctx: TickContext, region_id: int) -> bool:
    statement = (
        select(EventFootprintRow.event_entity_id)
        .join(EntityRow, EntityRow.id == EventFootprintRow.event_entity_id)
        .where(
            EventFootprintRow.region_entity_id == region_id,
            EntityRow.entity_type == EntityType.EVENT,
            EntityRow.engine_kind == EngineKind.DROUGHT,
            EntityRow.birth_epoch == ctx.epoch,
        )
        .limit(1)
    )
    return await ctx.session.scalar(statement) is not None


async def dry_siege(ctx: TickContext, community: EntityRow) -> bool:
    statement = select(SiegeRow.water).where(SiegeRow.besieged_entity_id == community.id, SiegeRow.status == SiegeStatus.ONGOING).order_by(SiegeRow.id)
    left = list(await ctx.session.scalars(statement))
    return any(water <= ctx.rules.siegecraft.famine_days for water in left)


async def stored_water(ctx: TickContext, community: EntityRow) -> int:
    if community.entity_type is not EntityType.SETTLEMENT:
        return 0
    works = await ctx.session.get(SettlementInfrastructureRow, community.id)
    return WATER_OF[works.water] if works is not None else 0


async def thirst_of(ctx: TickContext, community: EntityRow, region: RegionEnvironmentRow | None) -> int:
    table = ctx.rules.shortfall
    stored = await stored_water(ctx, community)
    want = 0.0
    if region is not None:
        if region.rainfall < table.dry_rainfall and table.dry_rainfall > 0:
            want += table.dry_thirst_pct * (table.dry_rainfall - region.rainfall) / table.dry_rainfall
        if await in_drought(ctx, region.entity_id):
            want += table.drought_thirst_pct
    want *= (PERCENT - stored) / PERCENT
    if await dry_siege(ctx, community):
        want += table.siege_thirst_pct
    return clamp_int(round_half_up(want), 0, PERCENT)


async def shelter_of(ctx: TickContext, community: EntityRow) -> int:
    if community.entity_type is not EntityType.SETTLEMENT:
        return 0
    profile = await ctx.session.get(SettlementProfileRow, community.id)
    population = stat(community, "population") or 0
    if profile is None or population <= 0:
        return 0
    return clamp_int(round_half_up(profile.homeless * PERCENT / population), 0, PERCENT)


async def outer_wants(ctx: TickContext, community: EntityRow, region: RegionEnvironmentRow | None) -> dict[ShortfallEffect, int]:
    return {ShortfallEffect.THIRST: await thirst_of(ctx, community, region), ShortfallEffect.SHELTER: await shelter_of(ctx, community)}


async def shortfall_rows(ctx: TickContext, community_id: int) -> dict[ShortfallEffect, CommunityShortfallRow]:
    rows = await kept_rows(ctx.session, CommunityShortfallRow, CommunityShortfallRow.community_entity_id, community_id)
    return {row.effect: row for row in rows}


async def kept_shortfalls(ctx: TickContext, community: EntityRow, found: Mapping[ShortfallEffect, int]) -> dict[ShortfallEffect, int]:
    rows = await shortfall_rows(ctx, community.id)
    note = ctx.rules.shortfall.note_pct
    kept: dict[ShortfallEffect, int] = {}
    for effect in SHORTFALLS:
        row = rows.get(effect)
        if row is None:
            row = CommunityShortfallRow(community_entity_id=community.id, effect=effect, short_pct=0, epoch=ctx.epoch, locked=[])
            ctx.session.add(row)
        before = row.short_pct
        if HELD_SHORT not in row.locked:
            row.short_pct = clamp_int(found.get(effect, 0), 0, PERCENT)
        row.epoch = ctx.epoch
        kept[effect] = row.short_pct
        if row.short_pct >= note > before:
            await record(
                ctx,
                "community.shortfall",
                roles={IncidentRole.VICTIM: community.id},
                facts={"effect": effect, "short": row.short_pct},
                place=community.id,
            )
    await ctx.session.flush()
    return kept
