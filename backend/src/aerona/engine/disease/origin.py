from sqlalchemy import select

from aerona.db.tables.disease import DiseaseProfileRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.engine.context import TickContext

ORIGIN_LOCK = "origin_incident_id"


async def origin_incident(ctx: TickContext, profile: DiseaseProfileRow | None) -> IncidentRow | None:
    if profile is None or profile.origin_incident_id is None:
        return None
    return await ctx.session.get(IncidentRow, profile.origin_incident_id)


async def origin_line(ctx: TickContext, profile: DiseaseProfileRow | None) -> str:
    incident = await origin_incident(ctx, profile)
    if incident is None:
        return ""
    return f", the sickness that first rose in epoch {incident.epoch}"


async def caused_by_origin(ctx: TickContext, row: ChronicleRow, profile: DiseaseProfileRow | None) -> None:
    incident = await origin_incident(ctx, profile)
    if incident is None:
        return
    written = await ctx.session.scalar(select(IncidentRow).where(IncidentRow.chronicle_id == row.id))
    if written is not None and written.id != incident.id and written.cause_incident_id is None:
        written.cause_incident_id = incident.id


async def mark_strain_origin(ctx: TickContext, profile: DiseaseProfileRow | None, row: ChronicleRow) -> None:
    if profile is None or ORIGIN_LOCK in profile.locked:
        return
    profile.origin_incident_id = await ctx.session.scalar(select(IncidentRow.id).where(IncidentRow.chronicle_id == row.id))
