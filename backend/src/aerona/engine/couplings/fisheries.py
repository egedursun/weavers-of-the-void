from sqlalchemy import select

from aerona.db.tables.crafts import CatchGroundRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.economy import ResourceProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.crafts import CatchRight
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind, LegitimacyBasis
from aerona.engine.context import TickContext
from aerona.engine.couplings.closures import closures_on
from aerona.engine.crafts.grounds import abundance_pct
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.polity.laws import enact
from aerona.engine.recording.record import record


async def keeper_town(ctx: TickContext, ground: CatchGroundRow) -> EntityRow | None:
    return await ctx.session.scalar(
        select(EntityRow)
        .where(EntityRow.location_id == ground.region_entity_id, EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.power_level.desc(), EntityRow.id)
        .limit(1)
    )


async def stock_left(ctx: TickContext, ground: CatchGroundRow) -> int | None:
    profile = await ctx.session.get(ResourceProfileRow, ground.source_entity_id)
    range_row = await ctx.session.get(SpeciesRangeRow, (ground.source_entity_id, ground.region_entity_id))
    return abundance_pct(ground, profile, range_row)


@reads("table.catch_grounds", "table.entities", "table.law_profiles", "table.resource_profiles", "table.species_ranges")
@writes("table.entities", "table.law_profiles")
async def closures(ctx: TickContext) -> None:
    table = ctx.rules.closures
    for ground in list(
        await ctx.session.scalars(select(CatchGroundRow).where(CatchGroundRow.right == CatchRight.COMMONS, CatchGroundRow.collapsed.is_(False)))
    ):
        left = await stock_left(ctx, ground)
        if left is None or left >= ground.collapse_at + table.margin or await closures_on(ctx.session, ground):
            continue
        town = await keeper_town(ctx, ground)
        if town is None or held(town.id):
            continue
        await enact(ctx, town, LawKind.CLOSED_SEASON, {}, basis=LegitimacyBasis.CUSTOM)
        ctx.count("closures_declared")
        await record(
            ctx,
            "fishery.closed",
            roles={IncidentRole.SUBJECT: town.id},
            facts={"ground": ground.source_entity_id, "stock": left, "collapse_at": ground.collapse_at},
            place=town.id,
        )
    await ctx.session.flush()
