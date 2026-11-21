from aerona.constants.units import PERCENT
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.labour import WorkerBodyRow
from aerona.domain.enums.labour import WorkerBodyForm
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.labour.bodies import LabourTally, home_of, trades_of
from aerona.engine.labour.hirers import shift_contentment, works_of
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.recording.record import record

RESERVE_PER_MEMBER = 2
CONTENTMENT_CAP = 5


async def tend_works(ctx: TickContext, body: WorkerBodyRow, tally: LabourTally) -> None:
    home = await home_of(ctx.session, body)
    if home is None:
        return
    works = await works_of(ctx.session, home.id, trades_of(body))
    if body.form is WorkerBodyForm.WORKER_COOPERATIVE:
        for work in works:
            if work.owner_node_id is None and not work.held:
                work.owner_node_id = body.faction_node_id
                tally.claimed += 1
                await record(
                    ctx,
                    "labour.works_claimed",
                    roles={IncidentRole.ACTOR: body.faction_node_id, IncidentRole.PLACE: home.id},
                    facts={"works": work.kind},
                    place=home.id,
                )
        await pay_by_work(ctx, body, home.id)
    if "works" not in (body.locked or []):
        body.works = sorted(work.id for work in works)


async def pay_by_work(ctx: TickContext, body: WorkerBodyRow, home_id: int) -> None:
    profile = await ctx.session.get(FactionProfileRow, body.faction_node_id)
    trades = trades_of(body)
    if profile is None or not trades or "treasury" in (profile.locked or []):
        return
    surplus = profile.treasury - body.members * RESERVE_PER_MEMBER
    if surplus <= 0:
        return
    paid = round_half_up(surplus * ctx.rules.labour.cooperative_payout_pct / PERCENT)
    profile.treasury -= paid
    lift = min(CONTENTMENT_CAP, paid // max(1, body.members))
    await shift_contentment(ctx, home_id, trades[0], lift)
