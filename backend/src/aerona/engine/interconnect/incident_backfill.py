from sqlalchemy import select

from aerona.catalog.incident_roles import INCIDENT_ROLES, positional_role
from aerona.db.fixups import fixup_due
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.war import WarSide
from aerona.engine.context import TickContext
from aerona.engine.interconnect.causes import war_cause_incident

ROLES_FIXUP = "incidents.roles_backfill"
WAR_OUTBREAK = "war.outbreak"


def recast(participants: list[IncidentParticipantRow], row: IncidentParticipantRow, role: IncidentRole) -> bool:
    if role is row.role or any(other.node_id == row.node_id and other.role is role for other in participants):
        return False
    row.role = role
    return True


async def _war_roles(ctx: TickContext, incident: IncidentRow, participants: list[IncidentParticipantRow]) -> int | None:
    node_ids = [row.node_id for row in participants]
    war = await ctx.session.scalar(select(WarRow).where(WarRow.event_entity_id.in_(node_ids)).limit(1))
    if war is None:
        return None
    sides = {row.entity_id: row.side for row in await ctx.session.scalars(select(WarSideRow).where(WarSideRow.war_id == war.id))}
    attacker = next((node for node, side in sides.items() if side is WarSide.ATTACKER), None)
    defender = next((node for node, side in sides.items() if side is WarSide.DEFENDER), None)
    for row in participants:
        side = sides.get(row.node_id)
        if side is not None and row.role is IncidentRole.SUBJECT:
            recast(participants, row, IncidentRole.ACTOR if side is WarSide.ATTACKER else IncidentRole.TARGET)
    if incident.cause_incident_id is None and attacker is not None and defender is not None:
        found = await war_cause_incident(ctx.session, war.cause, attacker, defender, incident.epoch)
        return found if found is not None and found != incident.id and found < incident.id else None
    return None


async def backfill_incident_roles(ctx: TickContext) -> int:
    if not await fixup_due(ctx.session, ROLES_FIXUP):
        return 0
    kinds = [*INCIDENT_ROLES, WAR_OUTBREAK]
    changed = 0
    linked = 0
    for incident in list(await ctx.session.scalars(select(IncidentRow).where(IncidentRow.kind.in_(kinds)).order_by(IncidentRow.id))):
        participants = list(
            await ctx.session.scalars(
                select(IncidentParticipantRow).where(IncidentParticipantRow.incident_id == incident.id).order_by(IncidentParticipantRow.position)
            )
        )
        for row in participants:
            role = positional_role(incident.kind, row.position)
            if row.role is IncidentRole.SUBJECT and role is not None and recast(participants, row, role):
                changed += 1
        if incident.kind == WAR_OUTBREAK:
            cause = await _war_roles(ctx, incident, participants)
            if cause is not None:
                incident.cause_incident_id = cause
                linked += 1
    ctx.session.add(AppliedFixupRow(key=ROLES_FIXUP, result={"roles": changed, "causes": linked}))
    await ctx.session.flush()
    return changed
