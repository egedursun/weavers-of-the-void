from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.renown import DeedClaimRow, DeedRow
from aerona.db.write_guard import held
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.relations import ContestEnd, ContestKind, ContestStake
from aerona.domain.enums.renown import ClaimKind, ClaimStatus
from aerona.engine.context import TickContext
from aerona.engine.mortal.justice import code_punishment, sentence
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.queries import living_entity
from aerona.engine.relations.contests import Bout, ContestTally, hold_contest
from aerona.engine.renown.deeds import DeedTally, claim_falsely, expose, share_deeds


async def punish(ctx: TickContext, claim: DeedClaimRow) -> bool:
    claimant = await living_entity(ctx.session, claim.claimant_node_id)
    if claimant is None or held(claimant.id) or not ctx.rng(seed_of("impostor", claim.id)).chance(ctx.rules.claims.punish_pct):
        return False
    return await sentence(ctx, claimant, CrimeKind.THEFT, await code_punishment(ctx, claimant.location_id, CrimeKind.THEFT))


async def test_claim(ctx: TickContext, deed: DeedRow, claim: DeedClaimRow, tally: DeedTally) -> None:
    table = ctx.rules.claims
    chance = table.verify_pct + deed.witnesses * table.witness_pct + (table.token_pct if deed.token else 0)
    if held(claim.claimant_node_id) or not ctx.rng(seed_of("verify", claim.id, ctx.epoch)).chance(min(PERCENT, chance)):
        return
    doer, claimant = await living_entity(ctx.session, deed.doer_node_id), await living_entity(ctx.session, claim.claimant_node_id)
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
        await claim_falsely(ctx, deed, tally)
    standing = await ctx.session.scalars(
        select(DeedClaimRow).where(DeedClaimRow.kind == ClaimKind.FALSE, DeedClaimRow.status == ClaimStatus.STANDING).order_by(DeedClaimRow.id)
    )
    for claim in list(standing):
        if "status" in claim.locked:
            continue
        found = await ctx.session.get(DeedRow, claim.deed_id)
        if found is not None:
            await test_claim(ctx, found, claim, tally)
    await ctx.session.flush()
