from sqlalchemy import select

from aerona.catalog.discovery import STRUCTURE_SUPERSEDED
from aerona.catalog.life.domain import STANDING_STATES
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.industry.methods import refit
from aerona.engine.recording.record import record as record_incident


async def date_structures(ctx: TickContext) -> int:
    dated = 0
    for technique, kinds in STRUCTURE_SUPERSEDED.items():
        known = dict(
            (
                await ctx.session.execute(
                    select(HolderTechniqueRow.holder_entity_id, HolderTechniqueRow.since_epoch).where(HolderTechniqueRow.technique == technique)
                )
            ).all()
        )
        if not known:
            continue
        rows = await ctx.session.scalars(
            select(StructureProfileRow).where(StructureProfileRow.kind.in_(list(kinds)), StructureProfileRow.construction_state.in_(list(STANDING_STATES)))
        )
        for row in list(rows):
            host = row.host_entity_id
            if host is None or host not in known or row.obsolete_since is not None or "obsolete_since" in row.locked or held(row.structure_entity_id):
                continue
            if (row.built_epoch or 0) < known[host]:
                row.obsolete_since = ctx.epoch
                dated += 1
    return dated


async def refit_structures(ctx: TickContext) -> int:
    refitted = 0
    rows = await ctx.session.scalars(
        select(StructureProfileRow).where(StructureProfileRow.obsolete_since.is_not(None)).order_by(StructureProfileRow.structure_entity_id)
    )
    for row in list(rows):
        host = await ctx.session.get(EntityRow, row.host_entity_id) if row.host_entity_id is not None else None
        work = await ctx.session.get(EntityRow, row.structure_entity_id)
        if host is None or work is None or host.status is not EntityStatus.CANON or "obsolete_since" in row.locked or held(host.id, work.id):
            continue
        if refit(ctx, host):
            row.obsolete_since, row.built_epoch = None, ctx.epoch
            refitted += 1
            await record_incident(ctx, "discovery.refitted", roles={IncidentRole.OWNER: host.id, IncidentRole.TARGET: work.id}, place=host.id)
    return refitted


async def obsolescence(ctx: TickContext) -> dict[str, int]:
    return {"structures_dated": await date_structures(ctx), "structures_refitted": await refit_structures(ctx)}
