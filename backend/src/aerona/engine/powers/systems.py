from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.powers import (
    MagicSystemLinkRow,
    MagicSystemRow,
    MagicSystemSourceRow,
    PowerSourceKnowledgeRow,
    SourceDensityRow,
)
from aerona.db.write_guard import held
from aerona.domain.enums.powers import SystemRelation
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.primitives.numbers import clamp_int, clamp_percent


async def mean_density(ctx: TickContext, system: MagicSystemRow) -> int | None:
    sources = select(MagicSystemSourceRow.source_id).where(MagicSystemSourceRow.system_id == system.id)
    mean = await ctx.session.scalar(select(func.avg(SourceDensityRow.density)).where(SourceDensityRow.source_id.in_(sources)))
    return round(mean) if mean is not None else None


async def drift(ctx: TickContext, system: MagicSystemRow) -> None:
    table = ctx.rules.magic_systems
    density = await mean_density(ctx, system)
    if density is not None and "prevalence" not in system.locked:
        step = clamp_int((density - system.prevalence) // 10, -table.drift, table.drift)
        system.prevalence = clamp_percent(system.prevalence + step)
    known = await ctx.session.scalar(
        select(func.avg(PowerSourceKnowledgeRow.level)).where(
            PowerSourceKnowledgeRow.source_id.in_(select(MagicSystemSourceRow.source_id).where(MagicSystemSourceRow.system_id == system.id))
        )
    )
    if known is not None and "predictability" not in system.locked and known >= system.predictability:
        system.predictability = clamp_percent(system.predictability + table.theory_gain)


async def share_roots(ctx: TickContext, system: MagicSystemRow) -> int:
    shared = 0
    rows = await ctx.session.scalars(
        select(MagicSystemLinkRow).where(
            MagicSystemLinkRow.relation == SystemRelation.SAME_ROOT,
            (MagicSystemLinkRow.first_system_id == system.id) | (MagicSystemLinkRow.second_system_id == system.id),
        )
    )
    for link in list(rows):
        other_id = link.second_system_id if link.first_system_id == system.id else link.first_system_id
        other = await ctx.session.get(MagicSystemRow, other_id)
        if other is None or "predictability" in other.locked or other.predictability >= system.predictability:
            continue
        gap = system.predictability - other.predictability
        other.predictability = clamp_percent(other.predictability + gap * ctx.rules.magic_systems.shared_discovery_pct // PERCENT // 10)
        shared += 1
    return shared


@reads("table.magic_system_links", "table.magic_system_sources", "table.magic_systems", "table.power_source_knowledge", "table.source_density")
@writes("table.magic_systems")
async def keep_systems(ctx: TickContext) -> None:
    for system in list(await ctx.session.scalars(select(MagicSystemRow).order_by(MagicSystemRow.id))):
        if held(system.scope_node_id):
            continue
        await drift(ctx, system)
        ctx.count("systems_sharing", await share_roots(ctx, system))
        ctx.count("magic_systems_kept")
    await ctx.session.flush()
