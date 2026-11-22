from sqlalchemy import select

from aerona.catalog.labour import TRADE_CLASS, TRADE_FORM
from aerona.catalog.life_traits import JOB_TRAITS, having
from aerona.db.tables.demography import LabourRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.labour import WorkerBodyRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.demography import Job
from aerona.domain.enums.faction import FactionKind, FactionRank
from aerona.domain.enums.labour import LegalStanding, WorkerBodyForm
from aerona.domain.enums.life_traits import JobTrait
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.labour.bodies import LabourTally, body_covering, new_body, standing_at, trades_of
from aerona.engine.labour.hirers import made_minds_at
from aerona.engine.phases.factions import found_faction
from aerona.engine.primitives.numbers import scaled_cap
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record

MADE_MIND_TRADES = having(JOB_TRAITS, JobTrait.MADE_MIND_TRADES)
UNFOUNDED = frozenset({Job.IDLE})


async def form_for(ctx: TickContext, community_id: int, trade: Job) -> WorkerBodyForm:
    if trade in MADE_MIND_TRADES and await made_minds_at(ctx.session, community_id):
        return WorkerBodyForm.MADE_MIND_COLLECTIVE
    if trade is Job.CRAFTING:
        guild = await ctx.session.scalar(
            select(FactionProfileRow.faction_entity_id)
            .where(FactionProfileRow.home_entity_id == community_id, FactionProfileRow.kind == FactionKind.CRAFT_GUILD)
            .order_by(FactionProfileRow.faction_entity_id)
            .limit(1)
        )
        if guild is not None:
            return WorkerBodyForm.COMPANION_SOCIETY
    return TRADE_FORM[trade]


async def maybe_found(ctx: TickContext, tally: LabourTally) -> None:
    table = ctx.rules.labour
    bitter = ctx.rules.mobility.bitter_satisfaction
    query = select(LabourRow).where(LabourRow.workers >= table.found_min_workers, LabourRow.job.not_in(sorted(UNFOUNDED)))
    rows = list(await ctx.session.scalars(query.order_by(LabourRow.community_entity_id, LabourRow.job)))
    done: set[int] = set()
    limit = scaled_cap(ctx.rules.factions.faction_cap, ctx.rules.factions.faction_cap_community_divisor, len({row.community_entity_id for row in rows}))
    for row in ctx.rng(f"labour.found.order.{ctx.epoch}").shuffled(rows):
        if len(done) >= limit:
            break
        if row.community_entity_id in done or held(row.community_entity_id):
            continue
        society = await ctx.session.get(CommunitySocietyRow, row.community_entity_id)
        if society is None or society.satisfaction(TRADE_CLASS[row.job]) >= bitter:
            continue
        if await body_covering(ctx.session, row.community_entity_id, row.job) is not None:
            continue
        community = await living_entity(ctx.session, row.community_entity_id)
        if community is None:
            continue
        banned = await standing_at(ctx.session, community.id) is LegalStanding.BANNED
        chance = table.found_chance_pct // 2 if banned else table.found_chance_pct
        if not ctx.rng(f"labour.found.{row.community_entity_id}.{row.job.value}.{ctx.epoch}").chance(chance):
            continue
        await found_body(ctx, community, [row.job], await form_for(ctx, community.id, row.job))
        done.add(row.community_entity_id)
        tally.founded += 1


async def found_body(ctx: TickContext, community: EntityRow, trades: list[Job], form: WorkerBodyForm, *, founder: int | None = None) -> WorkerBodyRow:
    faction = await found_faction(ctx, community, FactionKind.WORKER_BODY)
    body = new_body(ctx, faction.id, form, trades, await standing_at(ctx.session, community.id))
    if founder is not None:
        ctx.session.add(
            FactionMembershipRow(faction_entity_id=faction.id, mortal_entity_id=founder, rank=FactionRank.LEADER, joined_epoch=ctx.epoch, locked=[])
        )
    await ctx.session.flush()
    await record(
        ctx,
        "labour.body_founded",
        roles={IncidentRole.PRODUCT: faction.id, IncidentRole.ACTOR: founder, IncidentRole.PLACE: community.id},
        facts={"form": form, "trades": ", ".join(trade.value.replace("_", " ") for trade in trades_of(body))},
        place=community.id,
    )
    return body
