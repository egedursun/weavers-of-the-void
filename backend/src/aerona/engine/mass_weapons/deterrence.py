from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mass_weapons import DeterrencePostureRow
from aerona.db.write_guard import held
from aerona.domain.enums.loops import BalanceLoop
from aerona.domain.enums.mass_weapons import Posture
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.loops.delay import lagged
from aerona.engine.mass_weapons.book import ArsenalTally, armed, league_partners, postures_of, realms_of, rivals_of, weapons_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.recording.record import record

P = Posture
POSTURE_WEIGHT = total(
    Posture,
    {P.NONE: 0, P.DECLARED: 100, P.AMBIGUOUS: 60, P.FIRST_USE: 120, P.RETALIATION_ONLY: 100, P.SHARED_WITH_LEAGUE: 80},
)
DETERRENCE_CAP = 95


async def declare(ctx: TickContext, holder: EntityRow, toward: int | None, posture: Posture, tally: ArsenalTally) -> DeterrencePostureRow:
    found = next((row for row in await postures_of(ctx.session, holder.id) if row.toward_entity_id == toward), None)
    row = found or DeterrencePostureRow(holder_entity_id=holder.id, toward_entity_id=toward, locked=[])
    row.posture, row.declared_epoch = posture, ctx.epoch
    if found is None:
        row.credibility = clamp_int(ctx.rules.mass_weapons.test_credibility * (2 if await armed(ctx.session, holder.id) else 1), 0, PERCENT)
        ctx.session.add(row)
    await ctx.session.flush()
    await record(ctx, "war.posture_declared", roles={IncidentRole.ACTOR: holder.id, IncidentRole.TARGET: toward}, facts={"posture": posture})
    for rival in sorted(await rivals_of(ctx.session, holder.id)):
        for weapon in await weapons_of(ctx.session, holder.id):
            if rival not in (weapon.seen_by or []) and "seen_by" not in (weapon.locked or []):
                weapon.seen_by = sorted({*(weapon.seen_by or []), rival})
    return row


async def shields(ctx: TickContext, target_id: int) -> set[int]:
    realms = await realms_of(ctx.session, target_id)
    holders = set(realms)
    for realm in sorted(realms):
        for partner in sorted(await league_partners(ctx.session, realm)):
            if any(row.posture is Posture.SHARED_WITH_LEAGUE for row in await postures_of(ctx.session, partner)):
                holders.add(partner)
    return holders


async def deterrence(ctx: TickContext, attacker_id: int, target_id: int) -> int:
    attackers = await realms_of(ctx.session, attacker_id)
    best = 0
    for holder in sorted(await shields(ctx, target_id)):
        if holder in attackers:
            continue
        for row in await postures_of(ctx.session, holder):
            if row.toward_entity_id is not None and row.toward_entity_id not in attackers:
                continue
            best = max(best, ctx.rules.mass_weapons.deterrence_attack_cut_pct * row.credibility * POSTURE_WEIGHT[row.posture] // (PERCENT * PERCENT))
    return min(DETERRENCE_CAP, await lagged(ctx, BalanceLoop.MUTUAL_DETERRENCE, target_id, best, subject=attacker_id))


async def deterred(ctx: TickContext, attacker_id: int, target_id: int) -> bool:
    cut = await deterrence(ctx, attacker_id, target_id)
    return bool(cut) and ctx.rng(f"deterred.{attacker_id}.{target_id}.{ctx.epoch}").chance(cut)


async def expose_bluffs(ctx: TickContext, tally: ArsenalTally) -> None:
    query = select(DeterrencePostureRow).where(DeterrencePostureRow.posture != Posture.NONE).order_by(DeterrencePostureRow.id)
    for row in list(await ctx.session.scalars(query)):
        if held(row.holder_entity_id) or "credibility" in (row.locked or []) or await armed(ctx.session, row.holder_entity_id):
            continue
        if not ctx.rng(f"bluff.{row.id}.{ctx.epoch}").chance(ctx.rules.mass_weapons.bluff_exposure_pct):
            continue
        row.credibility = clamp_int(row.credibility - ctx.rules.mass_weapons.bluff_loss, 0, PERCENT)
        tally.bluffs += 1
        await record(ctx, "war.bluff_exposed", roles={IncidentRole.SUBJECT: row.holder_entity_id}, facts={"credibility": row.credibility})
