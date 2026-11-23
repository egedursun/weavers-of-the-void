from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.pacts import CLAIM_STATES, CONTESTABLE_CLAIMS
from aerona.catalog.renown import ACT_RENOWN
from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.repositories.chronicle import incident_for
from aerona.db.tables.culture import RumourRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.renown import DeedClaimRow, DeedRow, ReputationRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ActKind, Facet, MemoryKind, SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.renown import ClaimKind, ClaimStatus, ReputationAxis
from aerona.engine.context import TickContext
from aerona.engine.mind.book import skill_level, values_for
from aerona.engine.mind.ethics import ethic_reading
from aerona.engine.mind.memories import remember
from aerona.engine.mind.split import facets_of
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record
from aerona.engine.renown.book import acclaim

FACET_SPAN = 50


@dataclass
class DeedTally:
    recorded: int = 0
    heard: int = 0
    shared: int = 0
    false_claims: int = 0
    verified: int = 0
    exposed: int = 0
    disputed: int = 0


def axis_for(act: ActKind, reading: int) -> ReputationAxis | None:
    spec = ACT_RENOWN[act]
    if spec.always is not None and reading >= 0:
        return spec.always
    if reading > 0:
        return spec.approved
    return spec.condemned if reading < 0 else spec.always


async def record_deed(
    ctx: TickContext,
    doer_id: int,
    axis: ReputationAxis,
    magnitude: float,
    *,
    act: ActKind | None = None,
    skill: SkillKind | None = None,
    place_id: int | None = None,
    note_text: str | None = None,
    token: bool = False,
) -> DeedRow | None:
    if held(doer_id) or magnitude <= 0:
        return None
    query = select(DeedRow).where(DeedRow.doer_node_id == doer_id, DeedRow.axis == axis, DeedRow.epoch == ctx.epoch)
    query = query.where(DeedRow.act.is_(None) if act is None else DeedRow.act == act)
    found = await ctx.session.scalar(query.limit(1))
    size = clamp_int(magnitude, 0, PERCENT)
    if found is not None:
        if "magnitude" not in found.locked:
            found.magnitude = max(found.magnitude, size)
        found.token = found.token or token
        return found
    deed = DeedRow(
        doer_node_id=doer_id,
        incident_id=incident_for(ctx.session, doer_id, ctx.epoch),
        act=act,
        axis=axis,
        skill=skill,
        place_node_id=place_id,
        magnitude=size,
        witnesses=0,
        token=token,
        epoch=ctx.epoch,
        note=note_text,
        locked=[],
    )
    ctx.session.add(deed)
    await ctx.session.flush()
    ctx.session.add(new_claim(deed.id, doer_id, ClaimKind.TRUE, ctx.epoch))
    await ctx.session.flush()
    return deed


def new_claim(deed_id: int, claimant_id: int, kind: ClaimKind, epoch: int) -> DeedClaimRow:
    return DeedClaimRow(deed_id=deed_id, claimant_node_id=claimant_id, kind=kind, status=ClaimStatus.STANDING, credited=0, epoch=epoch, locked=[])


@memoized(DeedClaimRow)
async def claim_rows(session: AsyncSession, deed_id: int) -> tuple[DeedClaimRow, ...]:
    return tuple(await session.scalars(select(DeedClaimRow).where(DeedClaimRow.deed_id == deed_id).order_by(DeedClaimRow.id)))


async def claims_of(ctx: TickContext, deed_id: int) -> list[DeedClaimRow]:
    return list(await claim_rows(ctx.session, deed_id))


@memoized(DeedRow)
async def incidents_with_deeds(session: AsyncSession) -> frozenset[int]:
    return frozenset(await session.scalars(select(DeedRow.incident_id).where(DeedRow.incident_id.is_not(None))))


async def credit(ctx: TickContext, deed: DeedRow, community_id: int, amount: float, *, axis: ReputationAxis | None = None, witnessed: bool = False) -> int:
    claims = await claims_of(ctx, deed.id)
    impostor = next((claim for claim in claims if claim.kind in CONTESTABLE_CLAIMS and claim.status is ClaimStatus.STANDING), None)
    disputed = next((claim for claim in claims if claim.status is ClaimStatus.DISPUTED), None)
    shared = [claim for claim in claims if claim.kind is ClaimKind.SHARED and claim.status is not ClaimStatus.EXPOSED]
    true = next((claim for claim in claims if claim.kind is ClaimKind.TRUE), None)
    split = CLAIM_STATES[ClaimStatus.DISPUTED].credit_pct
    if impostor is not None and not witnessed:
        heads: list[tuple[DeedClaimRow | None, int]] = [(impostor, PERCENT)]
    elif disputed is not None:
        heads = [(disputed, split), (true, PERCENT - split)]
    else:
        heads = [(true, PERCENT)]
    credited = 0
    for claim, share in [*heads, *((claim, ctx.rules.claims.shared_pct) for claim in shared)]:
        if claim is None:
            continue
        gain = amount * share / PERCENT
        if await acclaim(ctx.session, claim.claimant_node_id, community_id, axis or deed.axis, amount=gain, epoch=ctx.epoch, skill=deed.skill) is not None:
            claim.credited += round(gain)
            credited += round(gain)
    return credited


async def deed_seen(ctx: TickContext, community_id: int, actor_id: int, act: ActKind, reading: int) -> DeedRow | None:
    axis = axis_for(act, reading)
    if axis is None:
        return None
    weight = max(abs(reading), PERCENT // 2) if ACT_RENOWN[act].always is axis else abs(reading)
    magnitude = ctx.rules.local_renown.act_magnitude * weight / PERCENT
    deed = await record_deed(ctx, actor_id, axis, magnitude, act=act, place_id=community_id)
    if deed is None:
        return None
    deed.witnesses += 1
    await credit(ctx, deed, community_id, magnitude, axis=axis, witnessed=True)
    return deed


async def best_craft(ctx: TickContext, mortal_id: int, skills: tuple[SkillKind, ...]) -> SkillKind | None:
    query = select(SkillRow).where(SkillRow.holder_node_id == mortal_id, SkillRow.skill.in_(list(skills))).order_by(SkillRow.level.desc(), SkillRow.id)
    row = await ctx.session.scalar(query.limit(1))
    return row.skill if row is not None else None


async def acclaim_deed(
    ctx: TickContext, doer_id: int, axis: ReputationAxis, magnitude: float, *, place_id: int | None, skill: SkillKind | None = None, token: bool = False
) -> None:
    deed = await record_deed(ctx, doer_id, axis, magnitude, skill=skill, place_id=place_id, token=token)
    if deed is not None and place_id is not None:
        deed.witnesses += 1
        await credit(ctx, deed, place_id, magnitude, witnessed=True)


async def hearsay(ctx: TickContext, tally: DeedTally) -> None:
    table = ctx.rules.local_renown
    rumours = list(await ctx.session.scalars(select(RumourRow).where(RumourRow.epoch == ctx.epoch, RumourRow.hops > 0).order_by(RumourRow.id)))
    for rumour in rumours:
        if held(rumour.carrier_entity_id):
            continue
        if rumour.incident_id not in await incidents_with_deeds(ctx.session):
            continue
        deeds = await ctx.session.scalars(select(DeedRow).where(DeedRow.incident_id == rumour.incident_id).order_by(DeedRow.id))
        for deed in deeds:
            axis = deed.axis
            if deed.act is not None:
                reading = await ethic_reading(
                    ctx.session, ctx.rules, rumour.carrier_entity_id, deed.act, await values_for(ctx.session, rumour.carrier_entity_id)
                )
                axis = axis_for(deed.act, reading) or deed.axis
            amount = deed.magnitude * table.hearsay_pct * rumour.fidelity / (PERCENT * PERCENT)
            if await credit(ctx, deed, rumour.carrier_entity_id, amount, axis=axis):
                tally.heard += 1


async def share_deeds(ctx: TickContext, deed: DeedRow, tally: DeedTally) -> None:
    if deed.incident_id is None:
        return
    query = select(IncidentParticipantRow.node_id).where(
        IncidentParticipantRow.incident_id == deed.incident_id, IncidentParticipantRow.role == IncidentRole.ACTOR
    )
    for node_id in await ctx.session.scalars(query):
        partner = await living_entity(ctx.session, node_id)
        if partner is None or partner.id == deed.doer_node_id or partner.entity_type is not EntityType.MORTAL or held(partner.id):
            continue
        if await ctx.session.scalar(select(DeedClaimRow.id).where(DeedClaimRow.deed_id == deed.id, DeedClaimRow.claimant_node_id == partner.id)) is None:
            bold = ctx.rng(seed_of("inflate", deed.id, partner.id)).chance(ctx.rules.claims.claim_pct * await boldness(ctx, partner.id))
            kind = ClaimKind.INFLATED if bold else ClaimKind.SHARED
            ctx.session.add(new_claim(deed.id, partner.id, kind, ctx.epoch))
            tally.shared += 1
            if bold:
                await record(ctx, "renown.claimed", roles={IncidentRole.ACTOR: partner.id, IncidentRole.VICTIM: deed.doer_node_id}, facts={"claim": kind})


async def boldness(ctx: TickContext, mortal_id: int) -> float:
    facets = await facets_of(ctx.session, mortal_id)
    vanity = (facets.get(Facet.VANITY, 0) + FACET_SPAN) / (2 * FACET_SPAN)
    guile = (await skill_level(ctx.session, mortal_id, SkillKind.DECEPTION) + PERCENT // 2) / PERCENT
    return vanity * guile * ctx.rules.claims.vanity_pct / PERCENT


async def claim_falsely(ctx: TickContext, deed: DeedRow, tally: DeedTally) -> int | None:
    table = ctx.rules.claims
    doer = await living_entity(ctx.session, deed.doer_node_id)
    if doer is None or deed.magnitude < table.claim_at or doer.location_id is None:
        return None
    near = await ctx.session.scalars(
        select(EntityRow)
        .where(
            await present_among(ctx.session, [doer.location_id]),
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.id != doer.id,
        )
        .order_by(EntityRow.id)
    )
    for rival in near:
        if held(rival.id):
            continue
        if not ctx.rng(seed_of("claim", deed.id, rival.id)).chance(table.claim_pct * await boldness(ctx, rival.id)):
            continue
        if await ctx.session.scalar(select(DeedClaimRow.id).where(DeedClaimRow.deed_id == deed.id, DeedClaimRow.claimant_node_id == rival.id)) is not None:
            return None
        ctx.session.add(new_claim(deed.id, rival.id, ClaimKind.FALSE, ctx.epoch))
        tally.false_claims += 1
        return rival.id
    return None


async def expose(ctx: TickContext, deed: DeedRow, claim: DeedClaimRow, tally: DeedTally) -> None:
    table = ctx.rules.claims
    claim.status, claim.settled_epoch = ClaimStatus.EXPOSED, ctx.epoch
    rows = list(await ctx.session.scalars(select(ReputationRow).where(ReputationRow.subject_node_id == claim.claimant_node_id)))
    places = sorted({row.community_node_id for row in rows})
    for row in rows:
        if row.axis is deed.axis and "value" not in row.locked:
            row.value = max(0, row.value - claim.credited)
    for place in places:
        await acclaim(ctx.session, claim.claimant_node_id, place, ReputationAxis.TRICKERY, amount=table.exposure_shame, epoch=ctx.epoch)
        await acclaim(ctx.session, deed.doer_node_id, place, deed.axis, amount=claim.credited / max(1, len(places)), epoch=ctx.epoch, skill=deed.skill)
    await remember(
        ctx.session,
        ctx.rules,
        holder_id=deed.doer_node_id,
        subject_id=claim.claimant_node_id,
        kind=MemoryKind.HUMILIATED_ME,
        magnitude=table.exposure_memory,
        epoch=ctx.epoch,
    )
    await record(
        ctx,
        "claim.exposed",
        roles={IncidentRole.ACCUSED: claim.claimant_node_id, IncidentRole.ACTOR: deed.doer_node_id},
        facts={"credited": claim.credited, "shame": table.exposure_shame, "deed": deed.axis},
        place=places[0] if places else None,
    )
    tally.exposed += 1
