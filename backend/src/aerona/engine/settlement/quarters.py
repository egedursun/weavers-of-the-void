from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.fixups import fixup_due
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.demography import CohortRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.evolution import PlagueResponseRow
from aerona.db.tables.settlement import DistrictRow
from aerona.db.write_guard import held
from aerona.domain.enums.demography import CohortCondition
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.evolution import PlagueResponse
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.settlement import BuildMaterial, DistrictKind
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.recording.record import record
from aerona.engine.settlement.book import Town
from aerona.engine.settlement.districts import density_pct
from aerona.engine.settlement.life import add_district

MOST_LEVEL = 5


async def displaced_in(session: AsyncSession, community_id: int) -> int:
    statement = select(func.coalesce(func.sum(CohortRow.count), 0)).where(
        CohortRow.community_entity_id == community_id, CohortRow.condition == CohortCondition.DISPLACED
    )
    return int(await session.scalar(statement) or 0)


async def holding_apart(ctx: TickContext, community_id: int) -> bool:
    statement = select(PlagueResponseRow.disease_entity_id).where(
        PlagueResponseRow.community_entity_id == community_id,
        PlagueResponseRow.response == PlagueResponse.QUARANTINE,
        or_(PlagueResponseRow.until_epoch.is_(None), PlagueResponseRow.until_epoch >= ctx.epoch),
    )
    return await ctx.session.scalar(statement.limit(1)) is not None


async def opened(ctx: TickContext, town: Town, kind: DistrictKind) -> DistrictRow:
    district = await add_district(ctx, town, kind, material=BuildMaterial.TIMBER)
    await record(ctx, "district.opened", roles={IncidentRole.PLACE: town.entity.id}, facts={"kind": kind}, place=town.entity.id)
    return district


def shelters(ctx: TickContext, camp: DistrictRow) -> int:
    return ctx.rules.urban.housing_per_level * density_pct(ctx.rules, DistrictKind.CAMP) // PERCENT * camp.level


async def settle_camp(ctx: TickContext, town: Town, camp: DistrictRow, displaced: int) -> None:
    if "kind" in camp.locked or ctx.epoch - camp.built_epoch < ctx.rules.districts.epochs(ctx.rules.districts.camp_settle_years):
        return
    camp.kind = DistrictKind.SLUMS if displaced > 0 else DistrictKind.RESIDENTIAL
    await record(ctx, "district.settled", roles={IncidentRole.PLACE: town.entity.id}, facts={"kind": camp.kind}, place=town.entity.id)


async def keep_camp(ctx: TickContext, town: Town) -> int:
    table = ctx.rules.districts
    displaced = await displaced_in(ctx.session, town.entity.id)
    camp = next((district for district in town.districts if district.kind is DistrictKind.CAMP), None)
    if camp is None:
        if displaced <= 0:
            return 0
        camp = await opened(ctx, town, DistrictKind.CAMP)
    elif displaced > shelters(ctx, camp) and camp.level < MOST_LEVEL and "level" not in camp.locked:
        if ctx.rng(f"camp.{town.entity.id}.{ctx.epoch}").chance(table.camp_growth):
            camp.level += 1
    if "fire_risk" not in town.profile.locked:
        town.profile.fire_risk = clamp_int(town.profile.fire_risk + table.camp_fire_risk * camp.level, 0, PERCENT)
    await settle_camp(ctx, town, camp, displaced)
    return camp.level


async def keep_lazaretto(ctx: TickContext, town: Town) -> int:
    lazaretto = next((district for district in town.districts if district.kind is DistrictKind.LAZARETTO), None)
    if lazaretto is None:
        if not await holding_apart(ctx, town.entity.id):
            return 0
        lazaretto = await opened(ctx, town, DistrictKind.LAZARETTO)
    return lazaretto.level


async def keep_quarters(ctx: TickContext, town: Town) -> int:
    return await keep_camp(ctx, town) + await keep_lazaretto(ctx, town)


CAMPS_FIXUP = "districts.w52"


async def backfill_camps(ctx: TickContext) -> int:
    if not await fixup_due(ctx.session, CAMPS_FIXUP):
        return 0
    statement = (
        select(CohortRow.community_entity_id)
        .join(EntityRow, EntityRow.id == CohortRow.community_entity_id)
        .where(CohortRow.condition == CohortCondition.DISPLACED, CohortRow.count > 0, EntityRow.entity_type == EntityType.SETTLEMENT)
        .group_by(CohortRow.community_entity_id)
    )
    camps = set(await ctx.session.scalars(select(DistrictRow.settlement_entity_id).where(DistrictRow.kind == DistrictKind.CAMP)))
    added = 0
    for town_id in await ctx.session.scalars(statement):
        if town_id in camps or held(town_id):
            continue
        ctx.session.add(
            DistrictRow(settlement_entity_id=town_id, kind=DistrictKind.CAMP, level=1, material=BuildMaterial.TIMBER, built_epoch=ctx.epoch, locked=[])
        )
        added += 1
    ctx.session.add(AppliedFixupRow(key=CAMPS_FIXUP, result={"camps": added}))
    await ctx.session.flush()
    return added
