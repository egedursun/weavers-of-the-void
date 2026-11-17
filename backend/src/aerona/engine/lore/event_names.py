from sqlalchemy import select

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.tellings import IncidentNameRow
from aerona.db.write_guard import held
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.queries import spoken_language
from aerona.language.generator import NameKind

SPEAKER_ROLES = (IncidentRole.PLACE, IncidentRole.ACTOR, IncidentRole.SUBJECT, IncidentRole.LEADER, IncidentRole.TARGET, IncidentRole.WITNESS)
NAME_PART = "name"


async def speakers_of(ctx: TickContext, incident: IncidentRow) -> list[int]:
    found = [incident.place_entity_id] if incident.place_entity_id is not None else []
    rows = await ctx.session.execute(
        select(IncidentParticipantRow.node_id, IncidentParticipantRow.role)
        .where(IncidentParticipantRow.incident_id == incident.id)
        .order_by(IncidentParticipantRow.position, IncidentParticipantRow.node_id)
    )
    by_role: dict[IncidentRole, list[int]] = {}
    for node, role in rows:
        by_role.setdefault(role, []).append(node)
    for role in SPEAKER_ROLES:
        found.extend(by_role.get(role, []))
    return list(dict.fromkeys(found))


async def name_happenings(ctx: TickContext) -> int:
    threshold = ctx.rules.records.naming_magnitude
    named = select(IncidentNameRow.incident_id)
    incidents = list(
        await ctx.session.scalars(
            select(IncidentRow)
            .where(IncidentRow.epoch >= ctx.epoch - 1, IncidentRow.magnitude >= threshold, IncidentRow.id.not_in(named))
            .order_by(IncidentRow.id)
        )
    )
    namer = Namer(ctx.session, ctx.rules)
    made = 0
    for incident in incidents:
        spec = INCIDENT_KINDS.get(incident.kind)
        if spec is None or not spec.told or NAME_PART in (incident.locked or []):
            continue
        for speaker in await speakers_of(ctx, incident):
            if held(speaker):
                continue
            language = await spoken_language(ctx.session, speaker)
            if language is None or held(language.id):
                continue
            word = await namer.from_language(language, seed_of("happening", incident.id), NameKind.GENERAL)
            if word:
                ctx.session.add(IncidentNameRow(incident_id=incident.id, name=word.capitalize(), language_entity_id=language.id, epoch=ctx.epoch, locked=[]))
                made += 1
            break
    await ctx.session.flush()
    return made
