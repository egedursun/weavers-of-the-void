from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.governance import BODY_RANKS, CULT_FORM, ORG_FORMS, RANK_WEIGHT, OrgForm
from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import CompanyProfileRow, CompanyShareRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.governance import InsolvencyCaseRow, OrgGovernanceRow, OrgSeatRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import FactionRank
from aerona.domain.enums.governance import GoverningBody, InsolvencyPath, InsolvencyStage, VoteBasis
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext

LEGACY_FIXUP = "governance.legacy_bodies"
COLLAPSE_KIND = "companies.collapsed"
ORG_TYPES = (EntityType.FACTION, EntityType.CULT)
SOLE_BODIES = frozenset({GoverningBody.FOUNDER, GoverningBody.HEAD, GoverningBody.MADE_MIND})
VOTE_LOCK = "vote_weight"


@dataclass
class SeedTally:
    bodies: int = 0
    seats: int = 0


async def organisations(ctx: TickContext) -> list[EntityRow]:
    return list(
        await ctx.session.scalars(select(EntityRow).where(EntityRow.entity_type.in_(ORG_TYPES), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id))
    )


async def form_of(ctx: TickContext, org: EntityRow) -> OrgForm:
    profile = await ctx.session.get(FactionProfileRow, org.id)
    return ORG_FORMS[profile.kind] if profile is not None else CULT_FORM


@memoized(FactionMembershipRow)
async def members_by_org(session: AsyncSession) -> dict[int, list[FactionMembershipRow]]:
    found: dict[int, list[FactionMembershipRow]] = {}
    query = select(FactionMembershipRow).order_by(FactionMembershipRow.faction_entity_id, FactionMembershipRow.mortal_entity_id)
    for row in await session.scalars(query):
        found.setdefault(row.faction_entity_id, []).append(row)
    return found


async def members_of(ctx: TickContext, org_id: int) -> list[FactionMembershipRow]:
    return list((await members_by_org(ctx.session)).get(org_id, []))


async def shares_of(ctx: TickContext, org_id: int) -> dict[int, int]:
    rows = await ctx.session.scalars(select(CompanyShareRow).where(CompanyShareRow.company_entity_id == org_id).order_by(CompanyShareRow.holder_node_id))
    return {row.holder_node_id: row.share for row in rows if row.share > 0}


async def leader_of(ctx: TickContext, org: EntityRow) -> int | None:
    profile = await ctx.session.get(FactionProfileRow, org.id)
    if profile is not None and profile.leader_entity_id is not None:
        return profile.leader_entity_id
    for row in await members_of(ctx, org.id):
        if row.rank is FactionRank.LEADER:
            return row.mortal_entity_id
    return None


async def seed_governance(ctx: TickContext) -> SeedTally:
    tally = SeedTally()
    legacy = await ctx.session.get(AppliedFixupRow, LEGACY_FIXUP) is None
    for org in await organisations(ctx):
        if held(org.id) or await ctx.session.get(OrgGovernanceRow, org.id) is not None:
            continue
        form = await form_of(ctx, org)
        company = await ctx.session.get(CompanyProfileRow, org.id) is not None
        body = form.body if company or not legacy else GoverningBody.HEAD
        head = await leader_of(ctx, org)
        ctx.session.add(
            OrgGovernanceRow(
                org_node_id=org.id,
                decision_body=GoverningBody.SHAREHOLDERS_MEETING if company else body,
                head_selection=form.selection,
                head_node_id=head,
                term_epochs=ctx.rules.governance.term_epochs,
                term_ends_epoch=ctx.epoch + ctx.rules.governance.term_epochs,
                vote_basis=VoteBasis.BY_SHARE if company else form.basis,
                quorum_pct=ctx.rules.governance.quorum_pct,
                since_epoch=ctx.epoch,
                locked=[],
            )
        )
        tally.bodies += 1
    if legacy:
        cases = await record_past_collapses(ctx)
        ctx.session.add(AppliedFixupRow(key=LEGACY_FIXUP, result={"bodies": tally.bodies, "cases": cases}))
    await ctx.session.flush()
    return tally


async def record_past_collapses(ctx: TickContext) -> int:
    rows = await ctx.session.execute(
        select(IncidentRow.epoch, IncidentParticipantRow.node_id)
        .join(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
        .where(IncidentRow.kind == COLLAPSE_KIND, IncidentParticipantRow.role == IncidentRole.SUBJECT)
        .order_by(IncidentRow.id)
    )
    made = 0
    for epoch, debtor in rows:
        if await ctx.session.get(EntityRow, debtor) is None:
            continue
        ctx.session.add(
            InsolvencyCaseRow(
                debtor_node_id=debtor,
                creditors=[],
                path=InsolvencyPath.LIQUIDATION,
                stage=InsolvencyStage.CLOSED,
                started_epoch=epoch,
                ended_epoch=epoch,
                locked=[],
            )
        )
        made += 1
    return made


def apportioned[K: (int, str)](weights: dict[K, float], room: int) -> dict[K, int]:
    whole = sum(weights.values())
    if whole <= 0 or room <= 0:
        return dict.fromkeys(weights, 0)
    exact = {key: value * room / whole for key, value in weights.items()}
    given = {key: int(value) for key, value in exact.items()}
    left = room - sum(given.values())
    for key in sorted(exact, key=lambda item: (-(exact[item] - given[item]), item))[:left]:
        given[key] += 1
    return given


async def wanted_seats(ctx: TickContext, row: OrgGovernanceRow) -> dict[int, float]:
    if row.decision_body is GoverningBody.NONE:
        return {}
    if row.decision_body in SOLE_BODIES:
        return {row.head_node_id: 1.0} if row.head_node_id is not None else {}
    if row.decision_body is GoverningBody.SHAREHOLDERS_MEETING:
        return {holder: float(share) for holder, share in (await shares_of(ctx, row.org_node_id)).items()}
    return await member_weights(ctx, row)


async def member_weights(ctx: TickContext, row: OrgGovernanceRow) -> dict[int, float]:
    ranks = BODY_RANKS[row.decision_body]
    seated = [member for member in await members_of(ctx, row.org_node_id) if member.rank in ranks]
    if row.vote_basis is VoteBasis.BY_RANK:
        return {member.mortal_entity_id: float(RANK_WEIGHT[member.rank]) for member in seated}
    if row.vote_basis is VoteBasis.BY_SENIORITY:
        return {member.mortal_entity_id: float(max(1, ctx.epoch - member.joined_epoch + 1)) for member in seated}
    if row.vote_basis is VoteBasis.BY_SHARE:
        shares = await shares_of(ctx, row.org_node_id)
        if shares:
            return {member.mortal_entity_id: float(shares.get(member.mortal_entity_id, 0)) for member in seated if shares.get(member.mortal_entity_id)}
    return {member.mortal_entity_id: 1.0 for member in seated}


@memoized(OrgSeatRow)
async def seats_by_org(session: AsyncSession) -> dict[int, list[OrgSeatRow]]:
    found: dict[int, list[OrgSeatRow]] = {}
    for row in await session.scalars(select(OrgSeatRow).order_by(OrgSeatRow.org_node_id, OrgSeatRow.member_node_id)):
        found.setdefault(row.org_node_id, []).append(row)
    return found


async def seats_of(ctx: TickContext, org_id: int) -> list[OrgSeatRow]:
    return list((await seats_by_org(ctx.session)).get(org_id, []))


async def sync_seats(ctx: TickContext, row: OrgGovernanceRow) -> int:
    wanted = await wanted_seats(ctx, row)
    current = {seat.member_node_id: seat for seat in await seats_of(ctx, row.org_node_id)}
    kept = {member: seat for member, seat in current.items() if VOTE_LOCK in (seat.locked or [])}
    for member, stale in current.items():
        if member not in wanted and member not in kept:
            await ctx.session.delete(stale)
    room = max(0, PERCENT - sum(seat.vote_weight for seat in kept.values()))
    weights = apportioned({member: weight for member, weight in wanted.items() if member not in kept}, room)
    made = 0
    for member, weight in sorted(weights.items()):
        seat = current.get(member)
        if seat is None:
            ctx.session.add(OrgSeatRow(org_node_id=row.org_node_id, member_node_id=member, since_epoch=ctx.epoch, vote_weight=weight, locked=[]))
            made += 1
        else:
            seat.vote_weight = weight
    await ctx.session.flush()
    return made
