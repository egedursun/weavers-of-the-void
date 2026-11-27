from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.catalog.incident_kinds.onlookers import NOT_PARTY_ROLES
from aerona.catalog.land_memory import LAND_MEMORIES
from aerona.constants.units import PERCENT
from aerona.db.tables.interconnect import IncidentParticipantRow
from aerona.db.tables.polity import ClaimRow
from aerona.db.tables.region import RegionMemoryRow
from aerona.db.write_guard import held
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.region import RegionMemoryKind
from aerona.engine.context import TickContext
from aerona.engine.mind.memories import remember
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.recording.record import record

LINEAL = frozenset({RegionMemoryKind.FOUNDING, RegionMemoryKind.ACCESSION, RegionMemoryKind.UNION})


REMEMBERED_ROLES = (IncidentRole.PRODUCT, IncidentRole.SUBJECT, IncidentRole.ACTOR, IncidentRole.LEADER)


@dataclass
class Parties:
    nodes: list[int] = field(default_factory=list)
    roles: dict[int, IncidentRole] = field(default_factory=dict)

    def remembered(self) -> int | None:
        for wanted in REMEMBERED_ROLES:
            found = next((node for node in self.nodes if self.roles[node] is wanted), None)
            if found is not None:
                return found
        return self.nodes[0] if self.nodes else None


async def parties_of(ctx: TickContext, rows: list[RegionMemoryRow]) -> dict[int, Parties]:
    incidents = [row.incident_id for row in rows if row.incident_id is not None]
    found: dict[int, Parties] = defaultdict(Parties)
    if not incidents:
        return found
    for incident_id, node_id, role in await ctx.session.execute(
        select(IncidentParticipantRow.incident_id, IncidentParticipantRow.node_id, IncidentParticipantRow.role)
        .where(IncidentParticipantRow.incident_id.in_(incidents), IncidentParticipantRow.role.not_in(sorted(NOT_PARTY_ROLES)))
        .order_by(IncidentParticipantRow.incident_id, IncidentParticipantRow.position, IncidentParticipantRow.node_id)
    ):
        parties = found[incident_id]
        if node_id not in parties.roles:
            parties.nodes.append(node_id)
            parties.roles[node_id] = role
    return found


async def strengthen_line(ctx: TickContext, line: list[int]) -> int:
    if not line:
        return 0
    claims = await ctx.session.scalars(
        select(ClaimRow)
        .where((ClaimRow.claimant_entity_id.in_(line)) | (ClaimRow.house_entity_id.in_(line)), ClaimRow.ended_epoch.is_(None))
        .order_by(ClaimRow.id)
    )
    raised = 0
    for claim in claims:
        if "strength" in (claim.locked or []) or held(claim.claimant_entity_id):
            continue
        claim.strength = clamp_int(claim.strength + ctx.rules.land_memory.founding_claim, 0, PERCENT)
        raised += 1
    return raised


async def make_peace(ctx: TickContext, signers: list[int], row: RegionMemoryRow) -> None:
    goodwill = ctx.rules.land_memory.treaty_war_cut_pct
    for holder in signers:
        for subject in signers:
            if holder != subject and not held(holder):
                await remember(ctx.session, ctx.rules, holder_id=holder, subject_id=subject, kind=MemoryKind.MADE_PEACE, magnitude=goodwill, epoch=row.epoch)


async def nurse_grievance(ctx: TickContext, parties: list[int], row: RegionMemoryRow) -> None:
    if len(parties) < 2:
        return
    expeller, *expelled = parties
    for holder in expelled:
        if not held(holder):
            grievance = ctx.rules.land_memory.expulsion_grievance
            await remember(ctx.session, ctx.rules, holder_id=holder, subject_id=expeller, kind=MemoryKind.HARMED_ME, magnitude=-grievance, epoch=row.epoch)


async def answer_memories(ctx: TickContext, rows: list[RegionMemoryRow]) -> int:
    parties = await parties_of(ctx, rows)
    answered = 0
    for row in rows:
        if LAND_MEMORIES[row.kind].weight is None:
            continue
        party = parties.get(row.incident_id, Parties()) if row.incident_id is not None else Parties()
        involved = party.nodes
        if row.kind in LINEAL:
            await strengthen_line(ctx, involved)
        elif row.kind is RegionMemoryKind.TREATY:
            await make_peace(ctx, involved, row)
        elif row.kind is RegionMemoryKind.EXPULSION:
            await nurse_grievance(ctx, involved, row)
        await record(
            ctx,
            "memory.written",
            roles={IncidentRole.PLACE: row.region_entity_id, IncidentRole.SUBJECT: party.remembered()},
            facts={"memory": row.kind, "magnitude": row.magnitude},
            place=row.region_entity_id,
            world_id=row.world_id,
            cause=row.incident_id,
        )
        answered += 1
    return answered
