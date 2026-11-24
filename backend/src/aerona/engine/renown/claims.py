from sqlalchemy import select

from aerona.catalog.pacts import CONTESTABLE_CLAIMS, UNSETTLED_CLAIMS
from aerona.constants.units import PERCENT
from aerona.db.tables.renown import DeedClaimRow, DeedRow
from aerona.db.write_guard import held
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.relations import ContestEnd, ContestKind, ContestStake
from aerona.domain.enums.renown import ClaimKind, ClaimStatus
from aerona.engine.context import TickContext
from aerona.engine.mind.hooks import committed
from aerona.engine.mortal.justice import code_punishment, sentence
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record
from aerona.engine.relations.contests import Bout, ContestTally, hold_contest
from aerona.engine.renown.deeds import DeedTally, claim_falsely, expose, new_claim, share_deeds


async def punish(ctx: TickContext, claim: DeedClaimRow) -> bool:
    claimant = await living_entity(ctx.session, claim.claimant_node_id)
    if claimant is None or held(claimant.id) or not ctx.rng(seed_of("impostor", claim.id)).chance(ctx.rules.claims.punish_pct):
        return False
    return await sentence(ctx, claimant, CrimeKind.THEFT, await code_punishment(ctx, claimant.location_id, CrimeKind.THEFT))


async def dispute(ctx: TickContext, claim: DeedClaimRow, contender_id: int) -> bool:
    if claim.status is not ClaimStatus.STANDING or claim.kind not in CONTESTABLE_CLAIMS or "status" in claim.locked:
        return False
    if held(claim.claimant_node_id, contender_id):
        return False
    claim.status, claim.contested_by_node_id = ClaimStatus.DISPUTED, contender_id
    await record(
        ctx,
        "renown.disputed",
        roles={IncidentRole.ACTOR: contender_id, IncidentRole.OPPONENT: claim.claimant_node_id},
        facts={"claim": claim.kind},
    )
    return True


async def lay_claim(ctx: TickContext, deed: DeedRow, claimant_id: int, kind: ClaimKind) -> DeedClaimRow | None:
    known = await ctx.session.scalar(select(DeedClaimRow.id).where(DeedClaimRow.deed_id == deed.id, DeedClaimRow.claimant_node_id == claimant_id))
    if held(claimant_id) or known is not None:
        return None
    row = new_claim(deed.id, claimant_id, kind, ctx.epoch)
    ctx.session.add(row)
    await ctx.session.flush()
    await record(ctx, "renown.claimed", roles={IncidentRole.ACTOR: claimant_id, IncidentRole.VICTIM: deed.doer_node_id}, facts={"claim": kind})
    return row


async def test_claim(ctx: TickContext, deed: DeedRow, claim: DeedClaimRow, tally: DeedTally) -> None:
    table = ctx.rules.claims
    bonus = table.inflated_expose_pct if claim.kind is ClaimKind.INFLATED else 0
    chance = table.verify_pct + bonus + deed.witnesses * table.witness_pct + (table.token_pct if deed.token else 0)
    if held(claim.claimant_node_id) or not ctx.rng(seed_of("verify", claim.id, ctx.epoch)).chance(min(PERCENT, chance)):
        return
    doer, claimant = await living_entity(ctx.session, deed.doer_node_id), await living_entity(ctx.session, claim.claimant_node_id)
    if claim.status is ClaimStatus.STANDING and doer is not None and not deed.token and await dispute(ctx, claim, doer.id):
        tally.disputed += 1
        return
    if doer is not None and claimant is not None and doer.location_id == claimant.location_id and not held(doer.id):
        row = await hold_contest(ctx, Bout(ContestKind.TRIAL_OF_WISDOM, ContestStake.HONOUR, doer, claimant, place_id=doer.location_id), ContestTally())
        if row is not None and row.outcome is ContestEnd.DEFENDER:
            claim.status, claim.settled_epoch = ClaimStatus.VERIFIED, ctx.epoch
            tally.verified += 1
            return
    await expose(ctx, deed, claim, tally)
    await punish(ctx, claim)


async def tend_claims(ctx: TickContext, tally: DeedTally) -> None:
    for deed in list(await ctx.session.scalars(select(DeedRow).where(DeedRow.epoch == ctx.epoch).order_by(DeedRow.id))):
        tally.recorded += 1
        await share_deeds(ctx, deed, tally)
        liar = await claim_falsely(ctx, deed, tally)
        if liar is not None:
            seen = ctx.rng(seed_of("lie.seen", deed.id, liar)).chance(ctx.rules.ethics.lying_detect_pct)
            await committed(ctx, liar, ActKind.LYING, deed.doer_node_id, seen=seen)
    standing = await ctx.session.scalars(
        select(DeedClaimRow).where(DeedClaimRow.kind.in_(list(CONTESTABLE_CLAIMS)), DeedClaimRow.status.in_(list(UNSETTLED_CLAIMS))).order_by(DeedClaimRow.id)
    )
    for claim in list(standing):
        if "status" in claim.locked:
            continue
        found = await ctx.session.get(DeedRow, claim.deed_id)
        if found is not None:
            await test_claim(ctx, found, claim, tally)
    await forget_claims(ctx)
    await ctx.session.flush()


async def forget_claims(ctx: TickContext) -> None:
    old = ctx.epoch - ctx.rules.claims.epochs(ctx.rules.claims.forgotten_years)
    rows = await ctx.session.scalars(
        select(DeedClaimRow).where(DeedClaimRow.status == ClaimStatus.STANDING, DeedClaimRow.epoch <= old).order_by(DeedClaimRow.id)
    )
    for claim in list(rows):
        if "status" not in claim.locked and not held(claim.claimant_node_id):
            claim.status, claim.settled_epoch, claim.credited = ClaimStatus.FORGOTTEN, ctx.epoch, 0
